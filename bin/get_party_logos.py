#!/usr/bin/env python

import os
import sys
import json
import csv
from urlparse import urljoin
from io import BytesIO

from lxml import etree
import requests
from PIL import Image

sys.path.insert(0, '.')
from ocd_backend.utils.misc import slugify


def get_party_logo(party):
    try:
        r = requests.get(party['Website'])
    except Exception as e:
        r = None

    if r is None:
        return

    if r.status_code < 200 or r.status_code > 300:
        return

    try:
        html = etree.HTML(r.content)
    except Exception as e:
        html = None

    if html is None:
        return

    image = html.xpath('//meta[@property="og:image"]/@content|//link[contains(@rel, "icon")]/@href')
    if len(image) <= 0:
        image = html.xpath('//img[contains(@src, "logo")]/@src|//img[contains(@alt, "header")]/@src|//header//img/@src')

    slug = party['Partij'].lower().replace('/', '_')

    if len(image) <= 0:
        return

    try:
        r = requests.get(urljoin(r.url, image[0]), timeout=10)
    except Exception as e:
        r = None

    if r is None:
        return

    status = "x"
    try:
        img = Image.open(BytesIO(r.content))
        img.thumbnail((60, 60), Image.ANTIALIAS)
        img.save("%s.png" % (slug), "PNG")
        status = "."
    except Exception as e:
        pass
    print "%s %s -> %s" % (status, urljoin(r.url, image[0]), slug,)


def main(argv):
    feed_type = 'Website'
    parties = []

    with open('/opt/pfl/ocd_backend/data/lokaal.json') as in_file:
        parties = json.load(in_file)

    for party in parties:
        if party[feed_type] != '':
            get_party_logo(party)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
