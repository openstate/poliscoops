#!/usr/bin/env python

import os
import sys
import re
from pprint import pprint
from time import sleep

from elasticsearch.helpers import scan, bulk
backend_path = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..')

sys.path.insert(0, backend_path)

import ocd_backend
from ocd_backend import settings
from ocd_backend.es import elasticsearch
from ocd_backend.enrichers import clf
from ocd_ml.interestingness import featurize, class_labels


def regenerate_index(es_index):
        items = scan(
            elasticsearch,
            query=None,
            scroll='5m',
            raise_on_error=False, index=es_index, doc_type='item')

        actions = []
        for item in items:
            action = {
                "_index": es_index,
                '_op_type': 'update',
                "_type": 'item',
                "_id": item['_id'],
                "doc": {
                    "interestingness": class_labels[clf.predict(
                        [featurize(item['_source'])])[0]]
                }
            }
            actions.append(action)
            if len(actions) > 10000:
                bulk(elasticsearch, actions)
                sleep(5)
                actions = []
        print "%s" % (es_index,)

def main():
    regenerate_index('pfl_combined_index')
    return 0

if __name__ == '__main__':
    sys.exit(main())
