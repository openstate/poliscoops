import datetime
import math
import simplejson as json
import re
from urllib import urlencode
from pprint import pprint
import sys
import time
from urlparse import urlparse, urljoin
import hashlib
import os

from html5lib.filters.base import Filter

from flask import (
    Flask, abort, jsonify, request, redirect, render_template,
    stream_with_context, Response, url_for)

from jinja2 import Markup

import bleach
from bleach.sanitizer import Cleaner
import iso8601
import requests
from redis import StrictRedis

# locale.setlocale(locale.LC_TIME, "nl_NL")

app = Flask(__name__)

PAGE_SIZE = 10
REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_DB = 0

CHUNK_SIZE = 1024

REWRITE_IMAGE_LINKS_CHECK = 'http:'

FACETS = (
    # facet, label, display?, filter?
    ('date_from', 'Datum van', False, True,),
    ('date_to', 'Datum tot', False, True,),
    ('location', 'Locatie', True, True,),
    ('sources', 'Bron', True, True,),
    ('type', 'Soort', True, True,),
    ('politicians', 'Politici', True, True,),
    ('parties', 'Partijen', True, True,),
    ('topics', 'Onderwerpen', True, True,),
    ('polarity', 'Polariteit', True, True,),
    ('subjectivity', 'Sentiment', True, True,)
)


def allow_src(tag, name, value):
    if (tag == 'img') and (name in ('alt', 'height', 'width', 'src')):
        return True
    if (tag == 'a') and (name in ('href')):
        return True
    if (
        (tag == 'div') and (name in ('class')) and
        (value in ("facebook-external-link", "clearfix"))
    ):
        return True
    return False


def image_rewrite(url, doc_id):
    if url.startswith(REWRITE_IMAGE_LINKS_CHECK):
        img_hash = hashlib.md5('%s:%s' % (
            doc_id.encode('utf-8'), url.encode('utf-8'))).hexdigest()
        return url_for('link_proxy', hash=img_hash, url=url, id=doc_id)
    else:
        return url


@app.template_filter('party_image')
def do_party_image(s):
    if os.path.exists(
        '/opt/app/frontend/static/images/parties/%s.png' % (
            s.replace('/', '_'),)
    ):
            return s
    else:
        return 'backdrop'


@app.template_filter('unique')
def do_unique(s):
    return list(set(s))


@app.template_filter('html_cleanup')
def do_html_cleanup(s, result):
    class PflFilter(Filter):
        def __iter__(self):
            for token in Filter.__iter__(self):
                if token['type'] in ['StartTag', 'EmptyTag'] and token['data']:
                    if token['name'] == 'img':
                        for attr, value in token['data'].items():
                            token['data'][attr] = image_rewrite(urljoin(
                                result['meta']['original_object_urls']['html'],
                                token['data'][attr]), result['meta']['_id'])
                yield token
    ATTRS = {
        '*': allow_src
    }
    TAGS = ['img', 'a', 'p', 'div']
    cleaner = Cleaner(
        tags=TAGS, attributes=ATTRS, filters=[PflFilter], strip=True)
    try:
        return cleaner.clean(s).replace(
            '<img ', '<img class="img-responsive" ').replace('&amp;nbsp;', '')
    except TypeError:
        return u''


@app.template_filter('html_title_cleanup')
def do_html_title_cleanup(s, result):
    class PflFilter(Filter):
        def __iter__(self):
            for token in Filter.__iter__(self):
                if token['type'] in ['StartTag', 'EmptyTag'] and token['data']:
                    if token['name'] == 'img':
                        for attr, value in token['data'].items():
                            token['data'][attr] = image_rewrite(urljoin(
                                result['meta']['original_object_urls']['html'],
                                token['data'][attr]), result['meta']['_id'])
                yield token
    ATTRS = {
        '*': allow_src
    }
    TAGS = []
    cleaner = Cleaner(
        tags=TAGS, attributes=ATTRS, filters=[PflFilter], strip=True)
    try:
        return cleaner.clean(s).replace(
            '<img ', '<img class="img-responsive" ').replace('&amp;nbsp;', '')
    except TypeError:
        return u''

@app.template_filter('active_bucket')
def do_active_bucket(bucket, facet):
    if facet not in request.args:
        return u''
    if unicode(request.args[facet]) == unicode(bucket['key']):
        return u'active'
    return u''


@app.template_filter('url_for_search_page')
def do_url_for_search_page(params, gov_slug):
    url_args = {
    }
    if 'query' in request.args:
        url_args['query'] = request.args['query']

    for param, title, is_displayed, is_filter in FACETS:
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

    for param, title, is_displayed, is_filter in FACETS:
        if param in request.args:
            url_args[param] = request.args[param]

    if (
        facet in request.args and
        (unicode(bucket['key']) == (request.args[facet]))
    ):
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


@app.template_filter('timestamp_to_str')
def do_timestamp_to_str(s, format):
    try:
        return datetime.datetime.fromtimestamp(float(s) / 1000.0).strftime(format)
    except ValueError:
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
    URL = 'http://pfl_nginx_1/v0'
    # URL = 'https://api.poliflw.nl/v0'
    HEADERS = {'Host': 'api.poliflw.nl'}

    def sources(self):
        return requests.get('%s/sources' % (self.URL,), headers=self.HEADERS).json()

    def search(self, *args, **kwargs):
        es_query = {
            "facets": {
                "date": {
                    "order": {"_key": "asc"},
                    "interval": "month"  # for now ...
                },
                "location": {
                    "size": 1000
                },
                "sources": {},
                "type": {},
                "politicians": {},
                "parties": {},
                "topics": {},
                "polarity": {},
                "subjectivity": {}
            },
            "sort": "date",
            "order": "desc",
            "from": (kwargs['page'] - 1) * PAGE_SIZE,
            "size": PAGE_SIZE,
            "filters": {
                'types': {
                    'terms': ['item']
                },
                'date': {
                    'from': '1980-01-01T00:00:00'
                }
            }
        }

        if 'size' in kwargs:
            es_query['size'] = kwargs['size']
        if kwargs.get('query', None) is not None:
            es_query['query'] = kwargs['query']

        for facet, desc, is_displayed, is_filter in FACETS:
            try:
                main_facet, sub_facet = facet.split('_')
            except ValueError:
                main_facet = facet
                sub_facet = None
            facet_enabled = kwargs.get(facet, None) is not None
            if facet_enabled:
                if main_facet == 'date':
                    facet_value = datetime.datetime.fromtimestamp(
                        int(kwargs[facet]) / 1000)
                else:
                    facet_value = kwargs[facet]

                if sub_facet is not None:
                    es_query['filters'][main_facet][sub_facet] = facet_value.isoformat()
                else:
                    es_query['filters'][facet] = {'terms': [kwargs[facet]]}

        plain_result = requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
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
        result['query'] = es_query
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
            headers=self.HEADERS,
            data=json.dumps(es_query)).json()

    def get_by_id(self, id):
        return requests.get(
            '%s/combined_index/item/%s' % (self.URL, id,), headers=self.HEADERS).json()


api = BackendAPI()


@app.route("/")
def main():
    results = api.search(**{"size": 0, "page": 1})
    return render_template(
        'index.html',
        results=results,
        facets=FACETS,
        visible_facets=[f for f in FACETS if f[2]])


@app.route("/over")
def about():
    return render_template('about.html')


@app.route("/zoeken")
def search():
    search_params = {
        'page': int(request.args.get('page', '1')),
        'query': request.args.get('query', None)}

    for facet, desc, is_displayed, is_filter in FACETS:
        search_params[facet] = request.args.get(facet, None)


    results = api.search(**search_params)
    try:
        max_pages = int(math.floor(results['meta']['total'] / PAGE_SIZE))
        if (results['meta']['total'] % PAGE_SIZE) > 0:
            max_pages += 1
    except LookupError:
        max_pages = 0
    return render_template(
        'search_results.html', facets=FACETS, results=results,
        query=search_params['query'], page=search_params['page'],
        max_pages=max_pages, search_params=search_params,
        dt_now=datetime.datetime.now())


@app.route("/l/<location>/<party>/<id>")
def show(location, party, id):
    result = api.get_by_id(id)
    if '_id' not in result['meta']:
        result['meta']['_id'] = id
    return render_template('show.html', result=result)


@app.route("/idea")
def idea():
    url = 'http://idea.informer.com/tab6.js?domain=poliflw'

    r = requests.get(url)
    headers = dict(r.headers)
    idea_text = unicode(r.content)

    return idea_text
    #    return Response(response=idea_text, headers=headers)


@app.route("/r/<hash>")
def link_proxy(hash):
    url = request.args.get('url', None)
    if url is None:
        abort(404)

    doc_id = request.args.get('id', None)
    if doc_id is None:
        abort(404)

    img_hash = hashlib.md5('%s:%s' % (
        doc_id.encode('utf-8'), url.encode('utf-8'))).hexdigest()

    if hash != img_hash:
        abort(404)

    r = get_source_rsp(url)
    headers = dict(r.headers)

    def generate():
        for chunk in r.iter_content(CHUNK_SIZE):
            yield chunk

    return Response(generate(), headers=headers)


def get_source_rsp(url):
    return requests.get(
        url, stream=True, params=request.args)


@app.route("/_counters", methods=['POST'])
def get_counters():
    return jsonify(requests.post(
        'http://politags_web_1:5000/api/counters',
        data=request.data, headers={'Content-type': 'application/json'}
    ).content)


@app.route("/_question", methods=['POST'])
def get_question():
    return jsonify(requests.post(
        'http://politags_web_1:5000/api/articles/questions',
        data=request.data, headers={'Content-type': 'application/json'}
    ).content)


@app.route("/_answer/<question_id>", methods=['POST'])
def put_answer(question_id):
    return jsonify(requests.post(
        'http://politags_web_1:5000/api/questions/%s' % (question_id,),
        data=request.data, headers={'Content-type': 'application/json'}
    ).content)


@app.route("/_topic/<article_id>", methods=['POST'])
def put_topic(article_id):
    return jsonify(requests.post(
        'http://politags_web_1:5000/api/topics/%s' % (article_id,),
        data=request.data, headers={'Content-type': 'application/json'}
    ).content)


@app.route("/_email_subscribe", methods=['POST'])
def email_subscribe():
    return jsonify(requests.post(
        'http://binoas.openstate.eu/subscriptions/new',
        data=request.data).content)


@app.route("/unsubscribe", methods=['GET'])
def email_unsubscribe():
    data = {
        'query_id': request.args.get('query_id', None),
        'user_id': request.args.get('user_id', None),
    }
    if data['query_id'] is not None and data['user_id'] is not None:
        result = requests.delete(
            'http://binoas.openstate.eu/subscriptions/delete',
            data=json.dumps(data))
    else:
        result = None
    return render_template('unsubscribe.html', result=result)


def create_app():
    return app
