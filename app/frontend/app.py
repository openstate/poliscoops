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


@app.template_filter('url_for_search_page')
def do_url_for_search_page(params, gov_slug):
    url_args = {
        'gov_slug': gov_slug
    }
    if 'query' in request.args:
        url_args['query'] = request.args['query']
    url_args.update(params)
    url = url_for('search', **url_args)
    return url


@app.template_filter('active_bucket')
def do_active_bucket(bucket, facet):
    if facet not in request.args:
        return u''
    if request.args[facet] == bucket['key']:
        return u'active'
    return u''


@app.template_filter('link_bucket')
def do_link_bucket(bucket, facet):
    url_args = {
    }
    if 'query' in request.args:
        url_args['query'] = request.args['query']

    for param, title in FACETS:
        if param in request.args:
            url_args[param] = request.args[param]

    url_args[facet] = bucket['key']

    url = url_for('search', **url_args)
    return url


@app.template_filter('wordcloud_font_size')
def do_wordcloud_fontsize(c, total):
    max_size = 100 + 25 * math.log(total, 2)
    cur_size = 100 + 25 * math.log(c, 2)
    return '{p:.1f}%'.format(p=100 + ((cur_size * 100.0) / max_size))


@app.template_filter('tk_questions_format')
def do_tk_questions_format(s):
    return re.sub(
        r'^\s*(Vraag|Antwoord)\s+(\d+)', r"<h2>\1 \2</h2>", s, 0, re.M)


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


@app.template_filter('normalize_wob_title')
def do_normalize_wob_title(r):
    return r['title'].replace(r['meta']['original_object_id'], u'').strip()


@app.template_filter('split')
def do_split(s, delim):
    return s.split(delim)


@app.template_filter('get_original_wob_link')
def do_get_original_wob_link(r):
    if 'start_date' in r:
        ref_date = iso8601.parse_date(r['start_date'])
    else:
        ref_date = iso8601.parse_date(r['end_date'])
    url_type = 'html'
    time_diff = (
        time.mktime(datetime.datetime.now().utctimetuple()) -
        time.mktime(ref_date.utctimetuple()))
    if time_diff > (86400 * 365):
        url_type = 'alternate'
    if url_type in r['meta']['original_object_urls']:
        return r['meta']['original_object_urls'][url_type]
    else:
        return '#'


def redis_client():
    return StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


class BackendAPI(object):
    URL = 'https://api.poliflw.nl/v0'

    def sources(self):
        return requests.get('%s/sources' % (self.URL,)).json()

    def get_stats_in_period(self, date_from, date_to=None):
        es_query = {
            "size": 0,
            "filters": {
                "date": {
                    "from": date_from
                }
            },
            "facets": {
                "classification": {},
                "answer_classification": {},
                "additional_answer_classification": {},
                "extension_classification": {}
            }
        }

        if date_to is not None:
            es_query["filters"]["date"]["to"] = date_to

        try:
            result = requests.post(
                '%s/tk_qa_matches/search' % (self.URL,),
                data=json.dumps(es_query)).json()
        except Exception:
            result = {
                'facets': {
                    'dates': {
                        'entries': []
                    }
                },
                'hits': {
                    'hits': [],
                    'total': 0
                }
            }
        return result

    def stats_questions(self):
        es_query = {
            "size": 0,
            "facets": {
                "date": {
                    "interval": "year"
                },
                "description": {"size": 200},
                "answer_description": {"size": 200}
            }
        }

        try:
            result = requests.post(
                '%s/tk_qa_matches/search' % (self.URL,),
                data=json.dumps(es_query)).json()
        except Exception:
            result = {
                'facets': {
                    'dates': {
                        'entries': []
                    }
                },
                'hits': {
                    'hits': [],
                    'total': 0
                }
            }
        return result

    def search_questions(self, *args, **kwargs):
        es_query = {
            "facets": {
                "date": {},
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

        if 'gov_slug' in kwargs:
            es_query['filters']['collection'] = {
                'terms': [humanize(kwargs['gov_slug'])]}
        if 'size' in kwargs:
            es_query['size'] = kwargs['size']
        if kwargs.get('query', None) is not None:
            es_query['query'] = kwargs['query']
        if kwargs.get('category', None) is not None:
            es_query['filters']['categories'] = {
                'terms': [kwargs['category']]}
        if kwargs.get('status', None) is not None:
            es_query['filters']['status'] = {
                'terms': [kwargs['status']]}
        if kwargs.get('delay', None) is not None:
            delay_from, delay_to = kwargs['delay'].split('-', 1)
            script_stmnt = []
            if delay_from != '*':
                script_stmnt.append(
                    "(((doc['end_date'].value - doc['start_date'].value) / 86400000) > %s)" % (delay_from,))
            if delay_to != '*':
                script_stmnt.append(
                    "(((doc['end_date'].value - doc['start_date'].value) / 86400000) < %s)" % (delay_to,))
            es_query['filters']['delay'] = {
                "script": {"script": u' && '.join(script_stmnt)}}

        if kwargs.get('start_date', None) is not None:
            sd = datetime.datetime.fromtimestamp(
                int(kwargs['start_date']) / 1000)
            ed_month = sd.month + 1
            ed_year = sd.year
            if ed_month > 12:
                ed_month = 1
                ed_year += 1
            es_query['filters']['start_date'] = {
                'from': "%s-%s-01T00:00:00" % (sd.year, sd.month,),
                'to': "%s-%s-01T00:00:00" % (ed_year, ed_month,)}

        if kwargs.get('end_date', None) is not None:
            ed = datetime.datetime.fromtimestamp(
                int(kwargs['end_date']) / 1000)
            sd_month = ed.month + 1
            sd_year = ed.year
            if sd_month > 12:
                sd_month = 1
                sd_year += 1
            es_query['filters']['end_date'] = {
                'to': "%s-%s-01T00:00:00" % (sd_year, sd_month,),
                'from': "%s-%s-01T00:00:00" % (ed.year, ed.month,)}


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

    def get_by_id(self, gov_slug, id):
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
        'query': request.args.get('query', None),
        'date': request.args.get('date', None),
    }
    results = api.search_questions(**search_params)
    try:
        max_pages = int(math.ceil(results['meta']['total'] / PAGE_SIZE))
    except LookupError:
        max_pages = 0
    return render_template(
        'search_results.html', facets=FACETS, results=results,
        query=search_params['query'], page=search_params['page'],
        max_pages=max_pages, active_date=search_params['date'])




def create_app():
    return app
