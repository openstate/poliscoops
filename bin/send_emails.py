#!/usr/bin/env python

import os
import json
import sys
import re
from pprint import pprint

import redis
import requests

REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_DB = 0


def humanize(s):
    return u' '.join([x.capitalize() for x in s.split(u'-')])


class BackendAPI(object):
    URL = 'http://api.openwob.nl/v0'

    def find_by_id(self, gov_slug, id):
        es_query = {
            "filters": {
                "id": {"terms": [id]},
                'collection': {
                    'terms': [humanize(gov_slug)]
                },
                'types': {
                    'terms': ['item']
                }
            },
            "size": 1
        }

        return requests.post(
            '%s/search' % (self.URL,),
            data=json.dumps(es_query)).json()

api = BackendAPI()


def redis_client():
    return redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def get_all_email_keys(client):
    return client.keys('emails_*_*')


def send_mail(gov_slug, obj_id, email):
    wob = api.find_by_id(gov_slug, obj_id)
    print wob['item'][0]['title']


def perform_mail_run(client, gov_slug, obj_id):
    print "Getting for %s : %s" % (gov_slug, obj_id,)
    emails = client.hgetall('emails_%s_%s' % (gov_slug, obj_id,))
    for email, dummy in emails.iteritems():
        send_mail(gov_slug, obj_id, email)


def main():
    client = redis_client()
    keys = get_all_email_keys(client)
    for key in keys:
        dummy, gov_slug, obj_id = key.split('_', 2)
        perform_mail_run(client, gov_slug, obj_id)
    return 0

if __name__ == '__main__':
    sys.exit(main())
