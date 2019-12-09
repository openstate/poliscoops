#!/usr/bin/env python

import os
import sys
import re
import json
from pprint import pprint
from time import sleep
from collections import defaultdict

import requests

from elasticsearch.helpers import scan, bulk
backend_path = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..')

sys.path.insert(0, backend_path)

import ocd_backend
from ocd_backend import settings
from ocd_backend.es import elasticsearch
from ocd_backend.utils.as2 import AS2ConverterMixin
from ocd_backend.utils.voc import VocabularyMixin

class OldDataConverter(AS2ConverterMixin, VocabularyMixin):
    pass

def main(argv):
    if len(argv) > 1:
        url = argv[1]
    else:
        url = 'https://api.poliflw.nl/v0/search?sort=date&order=desc&size=100'
    data = requests.get(url, verify=False).json()
    output = []
    as2 = OldDataConverter()
    for i in data['item']:
        t = as2.as2_transform_old_object(i)
        as2.as2_index(t, t['item']['items'])
        output.append(t)
    pprint(output)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
