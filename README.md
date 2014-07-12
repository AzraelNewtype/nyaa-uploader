#nyaa-uploader

An automated torrent uploader for fansubbers.

##Requirements

[Python3](https://www.python.org/downloads/) with [PyYAML](http://pyyaml.org/) and [requests](http://docs.python-requests.org/en/latest/) modules installed.

##Setup

Fill in the dummy data in `creds.yaml.example`, and then remove the `.example`
from the filename. If you don't have a website for your group, just blank it
out. If you don't have a tokyotosho API key, you can blank that out too, and
simply don't use the -o flag. Anybody with an account can generate one though.

If you don't have a nyaa login/password though, **you probably aren't releasing
enough things that you need this script.**

Keep the file in the same dir as the script, whatever that is.

##Issues
- There hasn't been much testing on deliberately bad input. It will only hose your own accounts (or just break) so there hasn't been much need. 
- At the moment, it only supports a single nyaa login and tosho account, so if you are a person who uploads for multiple outfits, you'll have to keep multiple `creds.yaml` files around with different names, making sure the active group's is just named `creds.yaml`. This is definitely going to change.

##Help Output Example
```
usage: nyaa-uploader.py [-h] [-v] [-c CRC] [-g GROUP] [-t TITLE] [-p PART]
                        [-y TYPE] [-H] [-o] (-V VIDEO | -l) [-T TORRENT]
                        {lraw,lsub,araw,asub}

positional arguments:
  {lraw,lsub,araw,asub}
                        Nyaa/Tosho Category

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Print more data to stdout.
  -c CRC, --crc CRC     Override detected CRC
  -g GROUP, --group GROUP
                        Nyaa Group Field
  -t TITLE, --title TITLE
                        Nyaa Title Field
  -p PART, --part PART  Nyaa Part Field
  -y TYPE, --type TYPE  Nyaa Type Field
  -H, --hidden          Set Hidden on Nyaa?
  -o, --tosho           Submit torrent to tokyotosho.
  -V VIDEO, --video VIDEO
                        Video file torrent is named for.
  -l, --local           Use video/torrent in calling directory. Must be
                        exactly one.
  -T TORRENT, --torrent TORRENT
                        Torrent file, if it doesn't match video.
```
