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
    parser.add_argument('-v', '--verbose', help='Print more data to stdout.', action='store_true')
    parser.add_argument('-c', '--crc', help='Override detected CRC')
    parser.add_argument('-g', '--group', help="Nyaa Group Field")
    parser.add_argument('-t', '--title', help="Nyaa Title Field")
    parser.add_argument('-p', '--part', help="Nyaa Part Field")
    parser.add_argument('-y', '--type', help="Nyaa Type Field")
    parser.add_argument('-H', '--hidden', help="Set Hidden on Nyaa?", action="store_true")
    tosho_group = parser.add_mutually_exclusive_group()
    tosho_group.add_argument('-o', '--tosho', help='Submit torrent to tokyotosho.', action='store_true')
    tosho_group.add_argument('--up-tosho', help='Submit a torrent already uploaded to Nyaa '
                             'to tokyotosho.', action="store_true")
    parser.add_argument('cat', choices=["lraw", "lsub", "araw", "asub"], help="Nyaa/Tosho Category")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-V', '--video', help="Video file torrent is named for.")
    group.add_argument('-l', '--local', help="Use video/torrent in calling directory. "
                       "Must be exactly one.", action='store_true')
    parser.add_argument('-T', '--torrent', help="Torrent file, if it doesn't match video.")
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
        460: 'Missing Announce URL: You forgot to include a valid announce URL. Torrents using '
             'only DHT are not allowed, because this is most often just a mistake on behalf of '
             'the uploader.',
        461: 'Already Exists: This torrent already exists in the database.',
        462: 'Invalid File: The file you uploaded or linked to does not seem to be a torrent.',
        463: 'Missing Data: The form is missing required data like the category and/or the '
             'checkbox which confirms that you have read the rules.',
        520: 'Configuration Broken: Server-side error. Wait for a few minutes, and then notify '
             'Nyaa if the problem did not go away.'}[code]


def nyaa_login(session, settings):
    login_creds = {'login': settings['nyaa_login'], 'password': settings['nyaa_pass'],
                   'method': '1', 'submit': 'Submit'}
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
    crc_re = r'[\(\[]([\dA-F]{8})[\)\]]'
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


def tokyotosho_upload(cat, dl_url, url, api_key):
    payload = dict(type=tt_categories(args.cat), url=dl_url,
                   comment="Brought to you by the autoupload script Az hacked up.",
                   website=url, apikey=settings['tt_api_key'], send=True)
    tt_r = submit_to_tokyotosho(payload)
    try:
        tt_url = 'http://tokyotosho.info/details.php?id={0}'.format(tt_r.text.split(',')[1])
    except IndexError:
        die("Didn't find a comma, so the status can't have been returned correctly.")
    return tt_url


def link_log(logfile, url_type, url, append=False):
    if append:
        mode = 'a'
    else:
        mode = 'w'
    with open(logfile, mode) as o:
        o.write('{0}: {1}\n'.format(url_type, url))

if __name__ == "__main__":
    args = get_args()

    settings = get_settings()
    url = settings['website']

    if args.local:
        video, torrent = get_file_names(args)
    else:
        video = args.video
        if args.torrent:
            torrent = args.torrent
        else:
            torrent = video + '.torrent'

    link_data_filename = video + '.link.txt'

    if args.up_tosho:
        try:
            with open(link_data_filename) as links_raw:
                links = yaml.load(links_raw)
        except IOError:
            die("Failed to open {0}. Are you sure you uploaded this video's torrent?"
                .format(link_data_filename))

        try:
            dl_url = links['Nyaa Download URL']
        except IndexError:
            die("Can't find Nyaa Download URL in {0}. Did you edit it out?"
                .format(link_data_filename))
        tt_url = tokyotosho_upload(args.cat, dl_url, url, settings['tt_api_key'])
        link_log(link_data_filename, 'TT Status', tt_url, True)
        if args.verbose:
            print('Got TT Status: {0}'.format(tt_url))
        die('Submission complete')

    nyaa_cat = nyaa_categories(args.cat)
    if args.hidden:
        nyaa_hide = "1"
    else:
        nyaa_hide = "0"
    ul_payload = dict(name="", torrenturl="", catid=nyaa_cat, info=url,
                      hidden=nyaa_hide, rules="1", submit="Upload")
    if args.crc:
        crc = args.crc
    else:
        crc = get_crc(video)

    if args.verbose:
        if args.crc:
            print("Using supplied CRC: {0}".format(crc))
        else:
            print("Found CRC: {0}".format(crc))

    s = requests.session()
    nyaa_login(s, settings)

    if args.verbose:
        print("Logged in successfully.")

    ul_resp = upload_torrent(s, torrent, ul_payload)

    tid = get_new_torrent_id(ul_resp)
    view_url = "http://www.nyaa.se/?page=view&tid={0}".format(tid)
    dl_url = "http://www.nyaa.se/?page=download&tid={0}".format(tid)

    if args.verbose:
        print("Nyaa View Link: {0}".format(view_url))
        print("Nyaa Download Link: {0}".format(dl_url))

    meta_payload = dict(redirect=view_url, alias="", submission_key="", tid=tid,
                        group=args.group, title=args.title, part=args.part,
                        crc32=crc, type=args.type, submit="Submit",
                        namemod=video, infomod=url, descmod="")

    r = add_torrent_metadata(s, meta_payload)
    if args.verbose:
        print("Added following metadata successfully:")
        print(meta_payload)

    with open(link_data_filename, 'w') as o:
        o.write('Nyaa Download URL: {0}\n'.format(dl_url))
        o.write('Nyaa View URL: {0}\n'.format(view_url))

    if args.tosho:
        tt_url = tokyotosho_upload(args.cat, dl_url, url, settings['tt_api_key'])
        if args.verbose:
            print("Tokyotosho Status URL: {0}".format(tt_url))
        link_log(link_data_filename, 'TT Status', tt_url, True)
