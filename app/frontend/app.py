#!/usr/bin/python
# -*- coding: utf-8 -*-

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
from collections import OrderedDict

from html5lib.filters.base import Filter

from flask import (
    Flask, abort, jsonify, g, request, redirect, render_template,
    make_response, stream_with_context, Response, url_for)
from werkzeug.urls import url_encode
from flask_babel import Babel, format_datetime, gettext, ngettext, lazy_gettext

from jinja2 import Markup
from jinja2.exceptions import TemplateNotFound

import bleach
from bleach.sanitizer import Cleaner
import iso8601
import requests
from redis import StrictRedis
from lxml import etree
import pytz

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
    ('type', lazy_gettext('Type'), True, True, False,),
    ('generator', lazy_gettext('Origin'), True, True, False,),
    ('date_from', lazy_gettext('Date from'), False, True, False,),
    ('date_to', lazy_gettext('Date until'), False, True, False,),
    ('language', lazy_gettext('Language'), True, True, False,),
    ('location', lazy_gettext('Location'), True, True, False,),
    ('sources', lazy_gettext('Source'), True, True, False,),
    # TODO: magic sorting shit (see Joplin) below
    ('tag', lazy_gettext('Mentions'), True, True, {
        'rel': ['type', 'interestingness', 'polarity', 'subjectivity']
    },),
    # ('politicians', 'Politici', True, True,),
    # ('parties', 'Partijen', True, True,),
    ('actor', lazy_gettext('Created by'), True, True, False,),
    # ('topics', 'Onderwerpen', True, True,),
    ('polarity', lazy_gettext('Polarity'), False, False, False,),
    ('subjectivity', lazy_gettext('Sentiment'),False, False, False,),
    ('interestingness', lazy_gettext('Interestingness'), False, False, False,)
)

TAGS = {
    'laag': lazy_gettext('Low'),
    'hoog': lazy_gettext('High'),
    'partij': lazy_gettext('Party')
}

FACETS_MAPPING = {
    'language': lambda x: LANGUAGES.get(x.upper(), x),
    'location': lambda x: COUNTRIES.get(x.upper(), x),
    # currently only interestingness bu should be updated somehow
    'tag': lambda x: TAGS.get(x.lower(), x),
}

INTERVALS = OrderedDict([
    ('', lazy_gettext('Direct')),
    ('1d', lazy_gettext('Daily')),
    ('1w', lazy_gettext('Weekly'))])

DEFAULT_LANGUAGE = 'en'
BABEL_DEFAULT_LOCALE = 'en'

INTERFACE_LANGUAGES = OrderedDict([
    ('en', lazy_gettext('English')),
    ('de', lazy_gettext('German')),
    ('fr', lazy_gettext('French'))])
ARTICLE_LANGUAGES = OrderedDict([
    ('en', lazy_gettext('English')),
    ('de', lazy_gettext('German')),
    ('fr', lazy_gettext('French')),
    (None, lazy_gettext('Original language'))])

COUNTRIES = OrderedDict([
    ('AT', lazy_gettext('Austria')),
    ('BE', lazy_gettext('Belgium')),
    ('BG', lazy_gettext('Bulgaria')),
    ('HR', lazy_gettext('Croatia')),
    ('CY', lazy_gettext('Cyprus')),
    ('CZ', lazy_gettext('Czech Republic')),
    ('DK', lazy_gettext('Denmark')),
    ('EE', lazy_gettext('Estonia')),
    ('FI', lazy_gettext('Finland')),
    ('FR', lazy_gettext('France')),
    ('DE', lazy_gettext('Germany')),
    ('GR', lazy_gettext('Greece')),
    ('HU', lazy_gettext('Hungary')),
    ('IT', lazy_gettext('Italy')),
    ('IE', lazy_gettext('Ireland')),
    ('LV', lazy_gettext('Latvia')),
    ('LT', lazy_gettext('Lithuania')),
    ('LU', lazy_gettext('Luxembourg')),
    ('MT', lazy_gettext('Malta')),
    ('NL', lazy_gettext('Netherlands')),
    ('PL', lazy_gettext('Poland')),
    ('PT', lazy_gettext('Portugal')),
    ('RO', lazy_gettext('Romania')),
    ('ES', lazy_gettext('Spain')),
    ('SK', lazy_gettext('Slovakia')),
    ('SI', lazy_gettext('Slovenia')),
    ('SE', lazy_gettext('Sweden')),
    ('UK', lazy_gettext('United Kingdom')),
    ('EU', lazy_gettext('Eurpean Union')),
])

LANGUAGES = {
    'AT': lazy_gettext('German'),
    'BE': lazy_gettext('Dutch'),
    'BG': lazy_gettext('Bulgarian'),
    'HR': lazy_gettext('Croatian'),
    'CY': lazy_gettext('Greek'),
    'CZ': lazy_gettext('Czech'),
    'DK': lazy_gettext('Danish'),
    'EE': lazy_gettext('Estonian'),
    'FI': lazy_gettext('Finnish'),
    'FR': lazy_gettext('French'),
    'DE': lazy_gettext('German'),
    'GR': lazy_gettext('Greek'),
    'HU': lazy_gettext('Hungarian'),
    'IT': lazy_gettext('Italan'),
    'IE': lazy_gettext('Irish'),
    'LV': lazy_gettext('Latvian'),
    'LT': lazy_gettext('Lithuanian'),
    'LU': lazy_gettext('Luxembourgish'),
    'MT': lazy_gettext('Maltese'),
    'NL': lazy_gettext('Dutch'),
    'PL': lazy_gettext('Polish'),
    'PT': lazy_gettext('Portugese'),
    'RO': lazy_gettext('Romanian'),
    'ES': lazy_gettext('Spanish'),
    'SK': lazy_gettext('Slovakian'),
    'SI': lazy_gettext('Slovenian'),
    'SE': lazy_gettext('Swedish'),
    'EU': lazy_gettext('Eurpean Unionish'),
    'EN': lazy_gettext('English'),
    'UK': lazy_gettext('English')}

SORTING = {
    'recency': {
        'sort': 'item.created',
        'order': 'desc'
    },
    'relevancy': {
        'sort': None,
        'order': None
    }
}

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


def is_cookie_set(cookie_name):
    ck = request.cookies.get(cookie_name, None)
    return (ck is not None)


def get_languages():
    hl = request.args.get('hl', None) or request.cookies.get('hl', None) or DEFAULT_LANGUAGE
    rl = request.args.get('rl', None) or request.cookies.get('rl', None)
    return hl, rl


def get_locations():
    is_cookie_set = request.cookies.get('countries', None)
    if is_cookie_set:
        return request.cookies.get('countries', '').split(',')
    else:
        countries = api.countries()
        return [x['@id'].split('/')[-1] for x in countries['as:items']]


@babel.localeselector
def get_locale():
    hl, rl = get_languages()
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


def image_rewrite(url, doc_id, _external=False):
    if url.startswith(REWRITE_IMAGE_LINKS_CHECK):
        img_hash = hashlib.md5('%s:%s' % (
            doc_id.encode('utf-8'), url.encode('utf-8'))).hexdigest()
        return url_for('link_proxy', hash=img_hash, url=url, id=doc_id, _external=_external)
    else:
        return url


@app.context_processor
def inject_intervals():
    hl,rl = get_languages()
    redirect_url = request.args.get('redirect') or modify_query(hl=None, rl=None)
    selected_countries = get_locations()
    return dict(
        intervals=INTERVALS, hl=hl, rl=rl, search_params={},
        redirect=redirect_url, redirect_url_set=request.args.get('redirect'),
        cookie_hl_set=is_cookie_set('hl'),
        cookie_rl_set=is_cookie_set('rl'),
        cookie_countries_set=is_cookie_set('countries'),
        interface_languages=INTERFACE_LANGUAGES.items(),
        countries=COUNTRIES, selected_countries=selected_countries)

@app.template_global()
def modify_query(**new_values):
    args = request.args.copy()

    for key, value in new_values.items():
        args[key] = value

    return '{}?{}'.format(request.path, url_encode(args))


@app.template_filter('make_https')
def do_make_https(s):
    return re.sub(r'^http:\/\/', 'https://', s)

@app.template_filter('pls_show_label_for_facet')
def do_pls_show_label_for_facet(s, t):
    return FACETS_MAPPING[t](s)


@app.template_filter('pls_location')
def do_pls_location(s):
    return FACETS_MAPPING['location'](s)


@app.template_filter('pls_hostname')
def do_get_hostname(s):
    h = ''
    try:
        r = urlparse(s)
        h = r.netloc
    except Exception as e:
        pass
    return h.replace('www.', '')


@app.template_filter('pls_generate_article_template')
def do_generate_article_template(s):
    parts = re.split(r'\.\s+', s, 1)
    if len(parts) > 1:
        lead, rest_of_content = parts
        return u'<p class="lead">%s.</p><p class="text">%s</p>' % (
            lead, rest_of_content,)
    else:
        return u'<p class="text">%s</p>' % (s,)


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
            id = result.get('as:items', [{'@id': None}])[0].get('@id', None)
            return image_rewrite(urljoin(
                request.url,
                images[0]), id, True)
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
        return u'bucket-active'
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
    for a in ['query', 'hl', 'rl']:
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


def correct_iso8601_date_for_timezone(value):
    amsterdam_tz = pytz.timezone('Europe/Amsterdam')
    value_parsed = iso8601.parse_date(value)

    if re.match(r'(Z|\+)', value):
        return value_parsed
    else:
        # adjust for amsterdam time, dunno why -2 :P
        adjusted_dt = iso8601.parse_date('%s-02:00' % (value,))
        return adjusted_dt
    return value_parsed


def get_timesince_and_correct_for_timezone(value):
    amsterdam_tz = pytz.timezone('Europe/Amsterdam')
    current_dt = datetime.datetime.now(tz=amsterdam_tz)
    value_parsed = iso8601.parse_date(value)
    adjusted_dt = value_parsed
    try:
        current_tz = value_parsed.tzinfo
    except AttributeError:
        current_tz = None
    if current_tz is not None:
        diff = current_dt - value_parsed
    else:
        # adjust for amsterdam time
        adjusted_dt = iso8601.parse_date('%s+02:00' % (value,))
        diff = current_dt - adjusted_dt
    return diff

@app.template_filter('correct_timezone')
def correct_timezone(value):
    v = correct_iso8601_date_for_timezone(value)
    return v.isoformat()

# https://github.com/orionmelt/snoopsnoo/blob/3db203f356b9673c31aea7f362edd89467215a47/application/jinja_filters.py
@app.template_filter('timesince')
def timesince(value):
    """Returns textual representation of time since given datetime object."""
    diff = get_timesince_and_correct_for_timezone(value)
    periods = (
        (diff.days / 365, lazy_gettext("year"), lazy_gettext("years")),
        (diff.days / 30, lazy_gettext("month"), lazy_gettext("months")),
        (diff.days / 7, lazy_gettext("week"), lazy_gettext("weeks")),
        (diff.days, lazy_gettext("day"), lazy_gettext("days")),
        (diff.seconds / 3600, lazy_gettext("hour"), lazy_gettext("hours")),
        (diff.seconds / 60, lazy_gettext("minute"), lazy_gettext("minutes")),
        (diff.seconds, lazy_gettext("second"), lazy_gettext("seconds")),
    )
    for period, singular, plural in periods:
        if period:
            return "%d %s" % (period, singular if period == 1 else plural)
    return "a few seconds"

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
        if facet in FACETS_MAPPING.keys():
            output = FACETS_MAPPING[facet](output)
    else:
        if facet in FACETS_MAPPING.keys():
            output = FACETS_MAPPING[facet](bucket['key'])
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
    hl,rl = get_languages()
    return url_for(
        'show', as2_type=doc['@type'], id=doc['@id'].split('/')[-1], rl=rl,
        hl=hl)

@app.template_filter('as2_i18n_field')
def do_as2_i18n_field(s, result, l):
    map_field = "%sMap" % (s,)
    if l is not None:
        lng = l
    else:  # use language of article
        lng = result.get('@language', None)
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

@app.template_filter('pls_location')
def do_pls_location(s):
    try:
        result = COUNTRIES[s.upper()]
    except LookupError as e:
        result = s
    return result


class BackendAPI(object):
    #URL = 'http://nginx/v0'
    URL = 'https://api.poliscoops.com/v0'
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
                },
                "date": {
                    "to": "now"
                }
            }
        }

        print >>sys.stderr, kwargs
        for kw_opt in ['size', 'sort', 'order']:
            if kw_opt in kwargs:
                if kwargs[kw_opt] is not None:
                    es_query[kw_opt] = kwargs[kw_opt]
                else:
                    del es_query[kw_opt]

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
                    if re.match('\d{4}-\d{2}-\d{2}', kwargs[facet]):
                        facet_value = time.mktime(
                            iso8601.parse_date(kwargs[facet]).timetuple())
                    else:
                        facet_value = datetime.datetime.fromtimestamp(
                            int(kwargs[facet]) / 1000)
                else:
                    facet_value = kwargs[facet]

                if sub_facet is not None:
                    es_query['filters'][main_facet][sub_facet] = datetime.datetime.fromtimestamp(facet_value).strftime('%Y-%m-%d')  #.isoformat()
                else:
                    if isinstance(kwargs[facet], list):
                        es_query['filters'][facet] = {'terms': kwargs[facet]}
                    else:
                        es_query['filters'][facet] = {'terms': [kwargs[facet]]}

        print >>sys.stderr, json.dumps(es_query)
        plain_result = requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query))
        try:
            result = plain_result.json()
            # print >>sys.stderr, plain_result.content
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

    def locations(self, **args):
        es_query = {
            "filters": {
                "type": {"terms": ["Place"]}
            },
            "expansions": 3,
            "size": 400  # FIXME: increase size in the future
        }
        es_query.update(args)

        result = requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query))
        return result.json()

    def countries(self, **args):
        es_query = {
            "filters": {
                "type": {"terms": ["Place"]},
                "name": {"terms": COUNTRIES.keys()}
            },
            "expansions": 3,
            "size": 400  # FIXME: increase size in the future
        }
        es_query.update(args)

        result = requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query))
        return result.json()

    def find_by_id(self, id):
        return self.find_by_ids([id])

    def find_by_ids(self, ids, **args):
        es_query = {
            "filters": {
                "id": {"terms": ids}
            },
            "expansions": 3
        }
        es_query.update(args)

        result = requests.post(
            '%s/search' % (self.URL,),
            headers=self.HEADERS,
            data=json.dumps(es_query))
        return result.json()

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
    results = api.search(**{"size": 6, "page": 1})
    return render_template(
        'index.html',
        results=results,
        facets=FACETS,
        visible_facets=[f for f in FACETS if f[2]], current='home')


def _render_page(page_name):
    hl, rl = get_languages()
    try:
        res = render_template(
            '%s.html' % (page_name,),
            sub_template='%s.%s.html' % (page_name,hl,),
            current=page_name)
    except TemplateNotFound as e:
        res = render_template(
            '%s.html' % (page_name,), sub_template='%s.en.html' % (page_name,),
            current='search')
    return res


@app.route("/languages")
def languages():
    return render_template(
        'languages.html',
        article_languages=ARTICLE_LANGUAGES.items(), current='languages')

@app.route("/countries")
def countries():
    api_locations = api.countries()
    locations = {}
    for l in api_locations.get('as:items', []):
        first_key = l.get('nameMap', {}).keys()[0]
        locations[l['nameMap'][first_key]] = l['@id'].split('/')[-1]
    return render_template('countries.html',locations=locations, current='countries')


@app.route("/countries.json")
def countries_as_json():
    hl, rl = get_languages()
    # TODO: we can do internationalization of the country names here ...
    countries = api.countries()['as:items']
    result = [c for c in countries]
    for c in result:
        c['name'] = COUNTRIES[c['nameMap']['nl']];
        c['denonym'] = LANGUAGES[c['nameMap']['nl']];
    return jsonify(countries)

@app.route("/set_language")
def set_language():
    hl = request.args.get('hl', DEFAULT_LANGUAGE)
    rl = request.args.get('rl', None)
    redirect_url = request.args.get('redirect', None)
    resp = make_response(redirect(url_for('languages', redirect=redirect_url)))
    resp.set_cookie('hl', hl)
    if rl is not None:
        resp.set_cookie('rl', rl)
    else:
        resp.set_cookie('rl', '', expires=0)
    return resp

@app.route("/set_countries", methods=['POST'])
def set_countries():
    # note: this requires all countries to be in the dsata or it does not work
    countries = ','.join(request.form.getlist('countries'))
    redirect_url = request.form.get('redirect', None)
    print >>sys.stderr, "Redirect: %s" % (redirect_url,)
    if redirect_url is not None:
        resp = make_response(redirect(redirect_url))
    else:
        resp = make_response(redirect(url_for('countries')))
    resp.set_cookie('countries', countries)
    return resp


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


@app.route("/search")
def search():
    locations = [urljoin(urljoin(AS2_NAMESPACE, 'Place/'), l) for l in  get_locations()]
    search_params = {
        'page': int(request.args.get('page', '1')),
        'query': request.args.get('query', None)}

    for facet, desc, is_displayed, is_filter, sub_attr in FACETS:
        search_params[facet] = request.args.get(facet, None)
    if search_params['location'] is None:
        search_params['location'] = locations

    sort_key = request.args.get('sort', 'relevancy')
    if sort_key is not None:
        try:
            search_params.update(SORTING[sort_key])
        except LookupError as e:
            pass
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
        dt_now=datetime.datetime.now(), locations=locations,
        sort_key=sort_key, current='search')


@app.route("/<as2_type>/<id>")
def show(as2_type, id):
    ns_link = urljoin(urljoin(AS2_NAMESPACE, '%s/' % (as2_type,)), id)
    result = api.get_by_id(ns_link)
    results_as_json = json.dumps(result, indent=4)

    return render_template(
        'show.html', result=result, results=result,
        results_as_json=results_as_json, ns_link=ns_link)


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
    # See https://github.com/openstate/poliflw/blob/master/app/frontend/static/scripts/app.js#L60
    # actor is not registered in bones, hence use "tag"
    possible_filters = {
        'location': lambda x: {'terms': {'data.value.raw': [y for y in x.split(',') if not y.endswith('Place/')]}},
        'actor': lambda x: {'term': {'data.value.raw': x if x.startswith(AS2_NAMESPACE) else x.lower()}}}  # country filter for location?
    param2filter = {'location': 'location', 'actor': 'tag'}
    active_filters = []
    for f in possible_filters:
        if request.form.get(f, None) is None:
            continue
        # filters as nested queries do not work for some reason ...
        active_filters.append({
            "nested": {
                "path": "data",
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"data.key": param2filter[f]}},
                            possible_filters[f](request.form[f])
                        ]
                    }
                }
            }
        })


    # todo rl may be restricted to the original language...
    # we should be able to put a notification on it ...
    hl,rl = get_languages()
    #search_fields = ['title', 'description', 'data.value']
    search_fields = ['nameMap.%s' % (rl,), 'contentMap.%s' % (rl,)]

    search_query = {
        "nested": {
            "path": "data",
            "query": {
                "bool": {
                    "must": [
                        {"terms":{"data.key":search_fields}},
                        {"simple_query_string":{
                            "fields": ["data.value"],
                            "query": request.form.get('query', None),
                            "default_operator": "and"
                        }}
                    ]
                }
            }
        }
    }

    query = {
        "query": {
            "bool": {
                "must": [search_query]
            }
        }
    }



    if len(active_filters) > 0:
        query['query']['bool']['must'] += active_filters

    frequency = request.form.get('interval', '1h')
    if frequency.strip() == '':
        frequency = None

    request_data = {
        'application': 'poliscoops',
        'email': request.form.get('email', None),
        'frequency': frequency,
        'description': request.form.get('query', None),
        'query': query
    }
    # return jsonify(json.dumps(request_data))
    result = requests.post(
        'http://binoas.openstate.eu/subscriptions/new',
        data=json.dumps(request_data)).json()
    return render_template('subscribe.html', result=result)


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


@app.route("/<page_name>")
def show_page(page_name):
    try:
        res = _render_page(page_name)
    except TemplateNotFound as e:
        abort(404)
    return res


def create_app():
    return app
