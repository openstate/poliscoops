#!/usr/bin/env python

import sys
import json


def main():
    result = json.load(sys.stdin)
    try:
        print result[u'result'][u'resources'][0][u'url']
    except LookupError:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
