#!/usr/bin/env python
from datetime import datetime
import csv
import codecs
import json
from glob import glob
import gzip
from hashlib import sha1
import os
import re
import requests
import sys
import time
from urlparse import urljoin
from pprint import pprint

import click
from click.core import Command
from click.decorators import _make_command

from lxml import etree
import requests


LOCATIONS = []


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

def _get_normalized_locations():
    loc_path = os.path.join(
        os.path.dirname(__file__),
        '../ocd_backend/data/cbs-name2018-mapping.csv')
    result = {}
    with open(loc_path) as locations_in:
        locations = UnicodeReader(locations_in)
        headers = locations.next()
        for location in locations:
            record = dict(zip(headers, location))
            result[record[u'Key_poliflw']] = record[u'Alt_map']
    return result


def _normalize_location(location):
    if unicode(location) in LOCATIONS:
        return LOCATIONS[unicode(location)]
    return unicode(location)


def main():
    objects = json.load(sys.stdin)
    for obj in objects:
        obj[u'location'] = _normalize_location(obj[u'location'])
    json.dump(objects, sys.stdout, indent=2)


if __name__ == '__main__':
    sys.exit(main())
