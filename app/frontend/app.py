import datetime
import math
import simplejson as json
import re
from urllib import urlencode
from pprint import pprint
import sys

from flask import (
    Flask, abort, jsonify, request, redirect, render_template,
    stream_with_context, Response, url_for)

from jinja2 import Markup

import iso8601
import requests

# locale.setlocale(locale.LC_TIME, "nl_NL")

app = Flask(__name__)

PAGE_SIZE = 20


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


class BackendAPI(object):
    URL = 'http://api.openwob.nl/v0'

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
                "categories": {},
                "status": {},
                "start_date": {}
            },
            "sort": "start_date",
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
        if kwargs.get('query', None) is not None:
            es_query['query'] = kwargs['query']
        if kwargs.get('category', None) is not None:
            es_query['filters']['categories'] = {
                'terms': [kwargs['category']]}
        if kwargs.get('status', None) is not None:
            es_query['filters']['status'] = {
                'terms': [kwargs['status']]}
        # FIXME: we should do dates differently
        if kwargs.get('start_date', None) is not None:
            sd = datetime.datetime.fromtimestamp(int(kwargs['start_date']) / 1000)
            ed_month = sd.month + 1
            ed_year = sd.year
            if ed_month > 12:
                ed_month = 1
                ed_year += 1
            es_query['filters']['start_date'] = {
                'from': "%s-%s-01T00:00:00" % (sd.year, sd.month,),
                'to': "%s-%s-01T00:00:00" % (ed_year, ed_month,)}
        try:
            result = requests.post(
                '%s/search' % (self.URL,),
                data=json.dumps(es_query)).json()
        except Exception:
            result = {
                'hits': {
                    'hits': [],
                    'total': 0
                }
            }
        return result

    def category_stats(self, gov_slug, start_date=None, end_date=None):
        es_query = {
            "size": 0,
            "facets": {
                "categories": {}
            },
            "filters": {
                'collection': {
                    'terms': [humanize(gov_slug)]
                },
                'types': {
                    'terms': ['item']
                }
            }
        }

        try:
            print >>sys.stderr, json.dumps(es_query)
            result = requests.post(
                '%s/search' % (self.URL,),
                data=json.dumps(es_query)).json()
        except Exception as e:
            print >>sys.stderr, e
            result = {
                'facets': {
                    'categories': {
                        'buckets': []
                    }
                }
            }
        return result['facets']['categories']['buckets']

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


@app.route("/")
def main():
    return render_template('index.html')


@app.route("/stats")
def stats():
    results = api.stats_questions()
    return render_template('stats.html', results=results)


@app.route("/<gov_slug>")
def gov_home(gov_slug):
    categories = api.category_stats(gov_slug)
    results = api.search_questions(gov_slug=gov_slug, page=1, status='Open')
    return render_template(
        'gov.html', gov_slug=gov_slug, categories=categories, results=results)


@app.route("/<gov_slug>/zoeken")
def search(gov_slug):
    search_params = {
        'gov_slug': gov_slug,
        'page': int(request.args.get('page', '1')),
        'query': request.args.get('query', None),
        'category': request.args.get('category', None),
        'status': request.args.get('status', None),
        'start_date': request.args.get('start_date', None)
    }
    results = api.search_questions(**search_params)
    max_pages = int(math.ceil(results['meta']['total'] / PAGE_SIZE))
    return render_template(
        'search_results.html', results=results, query=search_params['query'],
        page=search_params['page'], active_category=search_params['category'],
        active_status=search_params['status'], max_pages=max_pages,
        active_start_date=search_params['start_date'],
        gov_slug=search_params['gov_slug'])


@app.route("/<gov_slug>/verzoek/<obj_id>")
def show(gov_slug, obj_id):
    result = api.find_by_id(gov_slug, obj_id)

    if result['meta']['total'] <= 0:
        abort(404)

    return render_template(
        'show.html', gov_slug=gov_slug, result=result['item'][0])


def create_app():
    return app
