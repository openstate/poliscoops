import datetime
import math
import simplejson as json
import re
from urllib import urlencode
from pprint import pprint
import sys
import time

from flask import (
    Flask, abort, jsonify, request, redirect, render_template,
    stream_with_context, Response, url_for)

from jinja2 import Markup

import iso8601
import requests
from redis import StrictRedis

# locale.setlocale(locale.LC_TIME, "nl_NL")

app = Flask(__name__)

PAGE_SIZE = 10
REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_DB = 0

FACETS = (
    ('date', 'Datum',),
    ('location', 'Locatie',),
    ('sources', 'Bron',),
    ('type', 'Soort',),
)


@app.template_filter('active_bucket')
def do_active_bucket(bucket, facet):
    if facet not in request.args:
        return u''
    if request.args[facet] == bucket['key']:
        return u'active'
    return u''


@app.template_filter('url_for_search_page')
def do_url_for_search_page(params, gov_slug):
    url_args = {
    }
    if 'query' in request.args:
        url_args['query'] = request.args['query']

    for param, title in FACETS:
        if param in request.args:
            url_args[param] = request.args[param]

    url_args.update(params)
    url = url_for('search', **url_args)
    return url


@app.template_filter('link_bucket')
def do_link_bucket(bucket, facet):
    url_args = {
    }
    if 'query' in request.args:
        url_args['query'] = request.args['query']

    for param, title in FACETS:
        if param in request.args:
            url_args[param] = request.args[param]

    if facet in request.args and (bucket['key'] == request.args[facet]):
        url_args[facet] = None
    else:
        url_args[facet] = bucket['key']

    url = url_for('search', **url_args)
    return url


@app.template_filter('iso8601_to_str')
def do_iso8601_to_str(s, format):
    try:
        return iso8601.parse_date(s).strftime(format)
    except iso8601.ParseError:
        return u''


@app.template_filter('iso8601_delay_in_days')
def do_iso8601_delay_in_days(q, a=None):
    s = a or datetime.datetime.now().isoformat()
    delay = iso8601.parse_date(s) - iso8601.parse_date(q)
    return delay.days


@app.template_filter('format_bucket')
def do_format_bucket(bucket, facet):
    output = u''
    if facet == 'date':
        output = bucket['key_as_string'].split('T')[0]
    else:
        output = bucket['key']
    return output


@app.template_filter('delay_buckets_humanize')
def do_delay_buckets_humanize(s):
    result = s.replace(
        '*-', 'minder dan '
    ).replace('.0', '').replace(
        '-*', ' of meer '
    )
    return result


@app.template_filter('nl2br')
def do_nl2br(s):
    return s.replace('\n', '<br>')


def humanize(s):
    return u' '.join([x.capitalize() for x in s.split(u'-')])


@app.template_filter('humanize')
def do_humanize(s):
    return humanize(s)


@app.template_filter('split')
def do_split(s, delim):
    return s.split(delim)


def redis_client():
    return StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


class BackendAPI(object):
    URL = 'http://frontend:5000/v0'

    def sources(self):
        return requests.get('%s/sources' % (self.URL,)).json()

    def search(self, *args, **kwargs):
        es_query = {
            "facets": {
                "date": {
                    "order": {"_key": "desc"}
                },
                "location": {},
                "sources": {},
                "type": {},
            },
            "sort": "date",
            "order": "desc",
            "from": (kwargs['page'] - 1) * PAGE_SIZE,
            "size": PAGE_SIZE,
            "filters": {
                'types': {
                    'terms': ['item']
                }
            }
        }

        if 'size' in kwargs:
            es_query['size'] = kwargs['size']
        if kwargs.get('query', None) is not None:
            es_query['query'] = kwargs['query']

        for facet, desc in FACETS:
            if kwargs.get(facet, None) is not None:
                if facet == 'date':
                    sd = datetime.datetime.fromtimestamp(
                        int(kwargs[facet]) / 1000)
                    ed_month = sd.month + 1
                    ed_year = sd.year
                    if ed_month > 12:
                        ed_month = 1
                        ed_year += 1
                    es_query['filters'][facet] = {
                        'from': "%s-%s-01T00:00:00" % (sd.year, sd.month,),
                        'to': "%s-%s-01T00:00:00" % (ed_year, ed_month,)}
                else:
                    es_query['filters'][facet] = {
                        'terms': [kwargs[facet]]}

        plain_result = requests.post(
            '%s/search' % (self.URL,),
            data=json.dumps(es_query))
        try:
            result = plain_result.json()
        except Exception as e:
            print >>sys.stderr, "ERROR (%s): %s" % (e.__class__, e)
            result = {
                'hits': {
                    'hits': [],
                    'total': 0
                }
            }
        return result

    def find_by_id(self, id):
        es_query = {
            "filters": {
                "id": {"terms": [id]},
                'types': {
                    'terms': ['item']
                }
            },
            "size": 1
        }

        return requests.post(
            '%s/search' % (self.URL,),
            data=json.dumps(es_query)).json()

    def get_by_id(self, id):
        return requests.get(
            '%s/combined_index/item/%s' % (self.URL, id,)).json()


api = BackendAPI()


@app.route("/")
def main():
    return render_template('index.html')


@app.route("/zoeken")
def search():
    search_params = {
        'page': int(request.args.get('page', '1')),
        'query': request.args.get('query', None)}

    for facet, desc in FACETS:
        search_params[facet] = request.args.get(facet, None)

    results = api.search(**search_params)
    try:
        max_pages = int(math.ceil(results['meta']['total'] / PAGE_SIZE))
    except LookupError:
        max_pages = 0
    return render_template(
        'search_results.html', facets=FACETS, results=results,
        query=search_params['query'], page=search_params['page'],
        max_pages=max_pages, search_params=search_params)




def create_app():
    return app
