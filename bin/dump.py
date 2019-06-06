#!/usr/bin/env python

import os
import sys
import re
import json
from pprint import pprint
from time import sleep
from collections import defaultdict

from elasticsearch.helpers import scan, bulk
backend_path = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..')

sys.path.insert(0, backend_path)

import ocd_backend
from ocd_backend import settings
from ocd_backend.es import elasticsearch


def main(argv):
    start_date = argv[1]
    end_date = argv[2]

    es_query = {
        "query": {
            "bool": {
                "filter": {
                    "range": {
                        "date": {
                            "from": start_date,
                            "to": end_date
                        }
                    }
                }
            }
        },
        "size": 100
    }

    items = scan(
        elasticsearch,
        query=es_query,
        scroll='5m',
        raise_on_error=False, index='pfl_combined_index', doc_type='item')

    print json.dumps(list(items))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
