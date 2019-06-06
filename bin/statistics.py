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

    parties = {}
    days = defaultdict(lambda: {})

    for item in items:
        day = item['_source']['date'][0:10]
        party = item['_source']['parties'][0]
        parties[party] = 1
        try:
            days[day][party] += 1
        except LookupError:
            days[day][party] = 1

    party_names = parties.keys()
    for day in days:
        for party in party_names:
            if party not in days[day]:
                days[day][party] = 0
    print json.dumps(days)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
