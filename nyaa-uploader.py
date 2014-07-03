#!/usr/bin/env python3.3
# -*- coding: utf-8 -*-

import argparse
import glob
import re
import requests
import sys
import yaml
from os import path

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--group", help="Nyaa Group Field")
    parser.add_argument("-t", "--title", help="Nyaa Title Field")
    parser.add_argument("-p", "--part", help="Nyaa Part Field")
    parser.add_argument("-y", "--type", help="Nyaa Type Field")
    parser.add_argument("cat", choices=["lraw", "lsub", "araw", "asub"], help="Nyaa/Tosho Category")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-V', '--video', help="Video file torrent is named for.")
    group.add_argument('-l', '--local', help="Use video/torrent in calling directory. Must be exactly one.",
                      action="store_true")
    parser.add_argument("-T", "--torrent", help="Torrent file, if it doesn't match video.")
    return parser.parse_args()

def die(msg="Undefined error."):
    print(msg)
    raise SystemExit

def get_file_names(args):
    torrents = glob.glob('*.torrent')
    vids = glob.glob('*.mkv') + glob.glob('*.mp4')

    if len(vids) != 1:
        die("Need to have exactly one video in this folder")

    if len(torrents) != 1 and not args.torrent:
        die("Need to have exactly one torrent in this folder")

    if args.torrent:
        t_out = args.torrent
    else:
        t_out = torrents[0]

    return (vids[0], t_out)

def nyaa_categories(cat):
    return {
        'lraw': '5_20',
        'lsub': '5_19',
        'araw': '1_11',
        'asub': '1_37'}[cat]

def tt_categories(cat):
    return {
        'lraw': 7,
        'lsub': 8,
        'araw': 7,
        'asub': 1}[cat]

def nyaa_error_codes(code):
    return {
        418: "I'm a teapot: You're doing it wrong.",
        460: "Missing Announce URL: You forgot to include a valid announce URL. Torrents using only DHT are not allowed, because this is most often just a mistake on behalf of the uploader.",
        461: 'Already Exists: This torrent already exists in the database.',
        462: 'Invalid File: The file you uploaded or linked to does not seem to be a torrent.',
        463: 'Missing Data: The form is missing required data like the category and/or the checkbox which confirms that you have read the rules.',
        520: 'Configuration Broken: Server-side error. Wait for a few minutes, and then notify Nyaa if the problem did not go away.'}[code]

def nyaa_login(session, settings):
    login_creds = {'login' : settings['nyaa_login'], 'password' : settings['nyaa_pass'],
                   'method' : '1', 'submit' : 'Submit'}
    session.post("http://www.nyaa.se/?page=login", data=login_creds)

def upload_torrent(session, t_in, ul_payload):
    try:
        torrent = {'torrent': open(t_in, 'rb')}
    except IOError:
        die("Torrent file {0} cannot be opened.".format(t_in))

    ul_response = session.post('http://www.nyaa.se/?page=upload', files=torrent, data=ul_payload)
    if ul_response.status_code == requests.codes.ok:
        return ul_response
    else:
        print("Server returned error code:")
        die(nyaa_error_codes(ul_response.status_code))

def get_crc(video):
    crc_re = r'\[[\w-]+\]\s?[\w\s-]+[\d{2}]?\s?\[([\dABCDEF]+)\]'
    m = re.search(crc_re, video)
    if m:
        return m.group(1)
    else:
        print("Failed to find CRC")
        return None

def get_new_torrent_id(resp):
    tid_re = r'<a href="http:\/\/www\.nyaa\.se\/\?page=view.*?tid=(\d+)">View your torrent\.<\/a>'

    m = re.search(tid_re, resp.text)
    return int(m.group(1))

def add_torrent_metadata(session, meta_payload):
    meta_response = session.post('http://www.nyaa.se/?page=manage&op=2', data=meta_payload)
    if meta_response.status_code == requests.codes.ok:
        return meta_response
    else:
        print("Server returned error code during metadata save:")
        die(nyaa_error_codes(meta_response.status_code))

def submit_to_tokyotosho(tt_payload):
    return requests.post('https://www.tokyotosho.info/new.php', data=tt_payload)

def get_settings():
    try:
        script_dir = path.dirname(path.realpath(sys.argv[0]))
        yaml_location = path.join(script_dir, "creds.yaml")
        with open(yaml_location) as y:
            settings = yaml.load(y)
    except IOError:
        die("Cannot load creds.yaml, cannot continue.")
    return settings

f = """
    dev-libs/boost-1.52.0-r6 requires >=dev-lang/python-3.2.5-r2:3.2
    dev-libs/libxml2-2.9.1-r1 requires >=dev-lang/python-3.2.5-r2:3.2[xml]
    dev-util/gdbus-codegen-2.36.4-r1 requires >=dev-lang/python-3.2.5-r2:3.2[xml]
    x11-proto/xcb-proto-1.8-r3 requires >=dev-lang/python-3.2.5-r2:3.2
"""

if __name__ == "__main__":
    args = get_args()
    settings = get_settings()

    url = settings['website']

    nyaa_cat = nyaa_categories(args.cat)
    ul_payload = dict(name="", torrenturl="", catid=nyaa_cat, info=url,
                      hidden="1", rules="1", submit="Upload" )
    if args.local:
        video, torrent = get_file_names(args)
    else:
        video = args.video
        if args.torrent:
            torrent = args.torrent
        else:
            torrent = video + '.torrent'

    crc = get_crc(video)

    s = requests.session()
    nyaa_login(s, settings)
    ul_resp = upload_torrent(s, torrent, ul_payload)

    tid = get_new_torrent_id(ul_resp)
    view_url = "http://www.nyaa.se/?page=view&tid={0}".format(tid)
    dl_url = "http://www.nyaa.se/?page=download&tid={0}".format(tid)


    meta_payload = dict(redirect=view_url, alias="", submission_key="", tid=tid, group=args.group,
                        title=args.title, part=args.part, crc32=crc, type=args.type, submit="Submit",
                        namemod=video, infomod=url, descmod="")

    r = add_torrent_metadata(s, meta_payload)
    link_data_filename = video + '.link.txt'
    tt_payload = dict(type=tt_categories(args.cat), url=dl_url,
                      comment="Brought to you by the autoupload script Az hacked up.",
                      website=url, apikey=settings['tt_api_key'],
                      send=True)
    tt_r = submit_to_tokyotosho(tt_payload)

    with open(link_data_filename, 'w') as o:
        o.write('Nyaa Download URL: {0}\n'.format(dl_url))
        o.write('TT Status,ID: {0}\n'.format(tt_r.text))
