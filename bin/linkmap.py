#!/usr/bin/env python

import sys
import os
import re
import json
import argparse

import requests
from lxml import etree

sys.path.insert(0, '.')

from ocd_backend.utils.linkmap import build_linkmap, save_linkmap, load_linkmap

def main(argv):

    parser = argparse.ArgumentParser(description='Makes linkmaps')
    parser.add_argument('-u', '--url', required=True,
                        help='The url to build a linkmap for')
    args = parser.parse_args(argv[1:])
    url = args.url
    html = etree.HTML(requests.get(url).content)
    existing = load_linkmap(url)
    linkmap = build_linkmap(url, html)
    #print json.dumps(linkmap, indent=2)
    if existing is not None and linkmap is not None:
        new_links = set(existing['links'] or []) - set(linkmap['links'])
        print(new_links)
    if not existing:
        save_linkmap(url, linkmap)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
