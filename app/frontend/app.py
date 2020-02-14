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
from copy import deepcopy
from operator import itemgetter, attrgetter

from html5lib.filters.base import Filter

from flask import (
    Flask, abort, jsonify, g, request, redirect, render_template,
    stream_with_context, Response, url_for)
from werkzeug.urls import url_encode
from flask.ext.babel import Babel, format_datetime, gettext, ngettext

from jinja2 import Markup

import bleach
from bleach.sanitizer import Cleaner
import iso8601
import requests
from redis import StrictRedis
from lxml import etree

# locale.setlocale(locale.LC_TIME, "nl_NL")

app = Flask(__name__)
babel = Babel(app)

PAGE_SIZE = 10
REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_DB = 0

CHUNK_SIZE = 1024

REWRITE_IMAGE_LINKS_CHECK = 'http:'

AS2_NAMESPACE = u'https://www.poliflw.nl/ns/voc/'

AS2_ACTIVITIES = [
    'Activity', 'InstransitiveActivity', 'Accept', 'Add', 'Announce',
    'Arrive', 'Block', 'Create', 'Delete', 'Dislike', 'Flag', 'Follow',
    'Ignore', 'Invite', 'Join', 'Leave', 'Like', 'Listen', 'Move', 'Offer',
    'Question', 'Reject', 'Read', 'Remove', 'TentativeReject',
    'TentativeAccept', 'Travel', 'Undo', 'Update', 'View']

AS2_ENTITIES = [
    'Object', 'Link', 'Collection', 'OrderedCollection', 'CollectionPage',
    'OrderedCollectionPage', 'Application', 'Group', 'Organization',
    'Person', 'Service', 'Article', 'Audio', 'Document', 'Event', 'Image',
    'Note', 'Page', 'Place', 'Profile', 'Relationship', 'Tombstone', 'Video',
    'Mention']

FACETS = (
    # facet, label, display?, filter?, sub filter attribute
    # ('hl', 'Display taal', False, False, False,),
    ('type', 'Soort', True, True, False,),
    ('generator', 'Afkomstig van', True, True, False,),
    ('date_from', 'Datum van', False, True, False,),
    ('date_to', 'Datum tot', False, True, False,),
    ('language', 'Taal', True, True, False,),
    ('location', 'Locatie', True, True, False,),
    ('sources', 'Bron', True, True, False,),
    # TODO: magic sorting shit (see Joplin) below
    ('tag', 'Genoemd', True, True, {
        'rel': ['type', 'interestingness', 'polarity', 'subjectivity']
    },),
    # ('politicians', 'Politici', True, True,),
    # ('parties', 'Partijen', True, True,),
    ('actor', 'Geplaatst door', True, True, False,),
    # ('topics', 'Onderwerpen', True, True,),
    ('polarity', 'Polariteit', False, False, False,),
    ('subjectivity', 'Sentiment',False, False, False,),
    ('interestingness', 'Interessantheid', False, False, False,)
)

DEFAULT_LANGUAGE = 'en'
BABEL_DEFAULT_LOCALE = 'en'

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None:
        return user.locale

    hl = request.args.get('hl', DEFAULT_LANGUAGE)
    return hl
    # otherwise try to guess the language from the user accept
    # header the browser transmits.  We support de/fr/en in this
    # example.  The best match wins.
    #return request.accept_languages.best_match(['de', 'fr', 'en'])


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone


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


@app.template_global()
def modify_query(**new_values):
    args = request.args.copy()

    for key, value in new_values.items():
        args[key] = value

    return '{}?{}'.format(request.path, url_encode(args))


@app.template_filter('party_image')
def do_party_image(s):
    if os.path.exists(
        '/opt/app/frontend/static/images/parties/%s.png' % (
            s.lower().replace('/', '_'),)
    ):
            return s.lower()
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
                                result['url'],
                                token['data'][attr]), result['@id'])
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


@app.template_filter('html_getimage')
def do_html_getimage(s, result):
    try:
        html = etree.HTML(s)
    except Exception as e:
        print e
        html = None
    if html is not None:
        images = html.xpath('//img/@src')

        if len(images) > 0:
            id = result.get('id', None) or result['meta']['_id']
            return image_rewrite(urljoin(
                result['meta']['original_object_urls']['html'],
                images[0]), id)
    return u'https://www.poliflw.nl/static/images/mstile-310x310.png'

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

    for param, title, is_displayed, is_filter, sub_attr in FACETS:
        if param in request.args:
            url_args[param] = request.args[param]

    url_args.update(params)
    url = url_for('search', **url_args)
    return url


@app.template_filter('link_bucket')
def do_link_bucket(bucket, facet):
    url_args = {
    }
    for a in ['query', 'hl']:
        if a in request.args:
            url_args[a] = request.args[a]

    for param, title, is_displayed, is_filter, sub_attr in FACETS:
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
        return format_datetime(iso8601.parse_date(s))
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
    elif str(bucket['key']).startswith(AS2_NAMESPACE):
        output = do_as2_i18n_field('name', bucket['object'], DEFAULT_LANGUAGE)
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


@app.template_filter('pfl_link')
def do_pfl_link(doc):
    return url_for(
        'show', as2_type=doc['@type'], id=doc['@id'].split('/')[-1])

@app.template_filter('as2_i18n_field')
def do_as2_i18n_field(s, result, l):
    map_field = "%sMap" % (s,)
    lng = l
    if map_field in result:
        if lng in result[map_field]:
            return result[map_field][lng]
        if DEFAULT_LANGUAGE in result[map_field]:
            return result[map_field][DEFAULT_LANGUAGE]
        k = result[map_field].keys()[-1]
        return result[map_field][k]
    else:
        try:
            r = result.get(s, None)
        except AttributeError as e:
            r = result
        return r

@app.template_filter('pfl_id_for_html_attr')
def do_pfl_id_for_html_attr(s):
    parts = s.split('/')
    if len(parts) > 1:
        return '%s-%s' % (parts[-2], parts[-1],)
    else:
        return s

def redis_client():
    return StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

@app.template_filter('pretty_json')
def do_pretty_json(s):
    return json.dumps(s, sort_keys=True,
                      indent=4, separators=(',', ': '))

class BackendAPI(object):
    URL = 'http://nginx/v0'
    # URL = 'https://api.poliflw.nl/v0'
    HEADERS = {'Host': 'api.poliscoops.com'}

    def sources(self):
        return requests.get('%s/sources' % (self.URL,), headers=self.HEADERS).json()

    def search(self, *args, **kwargs):
        results = self.bare_search(*args, **kwargs)
        print >>sys.stderr, "Got %s results bare search" % (
            len(results["as:items"]),)
        if results["as:totalItems"] <= 0:
            return results

        output = deepcopy(results)
        output['as:items'] = []
        o_count = 0
        o_match = 0
        for i in results["as:items"]:
            if i['@type'] in AS2_ACTIVITIES:
                o = self.find_by_id_and_date(i['@id'], i['created'])
            else:
                o = {'as:items': []}
            if len(o['as:items']) > 0:
                r = deepcopy(o['as:items'][0])
            else:
                r = i
            output['as:items'].append(r)

        print >>sys.stderr, "Got %s results and %s matches for id & created" % (
            o_count,o_match,)

        return output

    def bare_search(self, *args, **kwargs):
        es_query = {
            "facets": {
                "date": {
                    "order": {"_key": "asc"},
                    "interval": "month"  # for now ...
                },
                "location": {
                    "size": 10
                },
                "sources": {},
                "actor": {},
                "type": {},
                "generator": {},
                "tag": {
                    "size": 10
                },
                "language": {},
                # "politicians": {"size": 100},
                # "parties": {"size": 10000},
                # "collection": {"size": 10000},
                # "topics": {"size": 100},
                # "polarity": {},
                # "subjectivity": {},
                # "interestingness": {}
            },
            #"sort": "date",
            "expansions": 3,
            "sort": "item.created",
            "order": "desc",
            "from": (kwargs['page'] - 1) * PAGE_SIZE,
            "size": PAGE_SIZE,
            "filters": {
                'type': {
                    # FIXME: we cannot limit on this, since the actual object has the content
                    # thus, query on items that have content (Note, etc.), then find the
                    # creation events associated?? (find the last event where
                    # the object property points to the id)
                    # Alternatively we may need to limit on Note etc.
                    'terms': AS2_ENTITIES
                }
                # 'date': {
                #     'from': '1980-01-01T00:00:00'
                # }
            }
        }

        if 'size' in kwargs:
            es_query['size'] = kwargs['size']
        if kwargs.get('query', None) is not None:
            es_query['query'] = kwargs['query']

        for facet, desc, is_displayed, is_filter, sub_attr in FACETS:
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

        print >>sys.stderr, json.dumps(es_query)
        plain_result = requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query))
        try:
            result = plain_result.json()
            print >>sys.stderr, plain_result.content
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
        return self.find_by_ids([id])

    def find_by_ids(self, ids, **args):
        es_query = {
            "filters": {
                "id": {"terms": ids}
            }
        }
        es_query.update(args)

        return requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query)).json()

    def find_by_id_and_date(self, id, created_date):
        es_query = {
            "filters": {
                "object": {
                    "terms":[id]
                },
                "date": {
                    "from": created_date,
                    "to": created_date
                }
            },
            "expansions": 3,
            "size": 1
        }

        return requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query)).json()

    def get_by_id(self, id):
        return self.find_by_id(id)


api = BackendAPI()


@app.route("/")
def main():
    results = api.search(**{"size": 0, "page": 1})
    images = api.search(**{"query": "<img ", "sources": 'Partij nieuws', "page": 1})
    return render_template(
        'index.html',
        results=results,
        images=images,
        facets=FACETS,
        visible_facets=[f for f in FACETS if f[2]])


@app.route("/over")
def about():
    return render_template('about.html')


def get_facets_from_results(results):
    if "ibmsc:facets" not in results:
        return {}

    output = {}
    ids_to_find = []
    for f in results["ibmsc:facets"]:
        k = f["ibmsc:facet"]["dc:title"].lower()
        output[k] = {
            'buckets': [
                {
                    'key_as_string': x['dc:title'],
                    'key': x["ibmsc:label"],
                    'doc_count': x["ibmsc:weight"]
                } for x in f["ibmsc:facet"]["ibmsc:facetValue"]
            ]
        }
        ids_to_find += [x["ibmsc:label"] for x in f["ibmsc:facet"]["ibmsc:facetValue"] if str(x["ibmsc:label"]).startswith(AS2_NAMESPACE)]
    #print >>sys.stderr, "Should lookup facet buckets now: %s" % (ids_to_find,)
    result = api.find_by_ids(ids_to_find, size=len(ids_to_find))
    #print >>sys.stderr, result
    id_conversions = {x['@id']: x for x in result['as:items']}
    for f in results["ibmsc:facets"]:
        k = f["ibmsc:facet"]["dc:title"].lower()
        for b in output[k]['buckets']:
            if str(b["key"]).startswith(AS2_NAMESPACE):
                b['object'] = id_conversions[b["key"]]
    #print >>sys.stderr, output
    return output

def order_facets(facets):
    # for facet, desc, is_displayed, is_filter, sort_func in FACETS:
    #     if facet not in facets:
    #         continue
    #
    #     if not sort_func:
    #         continue
    #
    #     print >>sys.stderr, "Should do something interesting now for %s facet" % (facet,)
    #     print >>sys.stderr, facets[facet]
    #     facets[facet]['buckets'] = sort_func(facets[facet].get('buckets', []))
    #     print >>sys.stderr, facets[facet]
    return facets


@app.route("/zoeken")
def search():
    search_params = {
        'page': int(request.args.get('page', '1')),
        'query': request.args.get('query', None)}

    for facet, desc, is_displayed, is_filter, sub_attr in FACETS:
        search_params[facet] = request.args.get(facet, None)


    hl = request.args.get('hl', DEFAULT_LANGUAGE)

    results = api.search(**search_params)
    try:
        max_pages = int(math.floor(results['as:totalItems'] / PAGE_SIZE))
        if (results['as:totalItems'] % PAGE_SIZE) > 0:
            max_pages += 1
    except LookupError:
        max_pages = 0
    return render_template(
        'search_results.html', facets=FACETS, results=results,
        result_facets=order_facets(get_facets_from_results(results)),
        query=search_params['query'], page=search_params['page'],
        max_pages=max_pages, search_params=search_params,
        dt_now=datetime.datetime.now(), hl=hl)


@app.route("/<as2_type>/<id>")
def show(as2_type, id):
    ns_link = urljoin(urljoin(AS2_NAMESPACE, '%s/' % (as2_type,)), id)
    result = api.get_by_id(ns_link)
    return render_template(
        'show.html', result=result, results=result, ns_link=ns_link)


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
