#!/usr/bin/env python

import sys
import os
import re
from pprint import pprint
import glob
import pickle

import requests

sys.path.insert(0, '.')

from ocd_ml.interestingness import featurize


def main(argv):
    clf = pickle.load(open('interestingness.model', 'rb'))
    resp = requests.get('https://api.poliflw.nl/v0/search?sort=date&size=100', verify=False).json()

    res = clf.predict([featurize(o) for o in resp['item']])
    print res

    for obj, classification in zip(resp['item'], res):
        print "The following got a prediction of %s" % (classification,)
        print obj.get('description', '')
        print "-"*80
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
