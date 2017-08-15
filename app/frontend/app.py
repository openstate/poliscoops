import datetime
import math
import simplejson as json
import re

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
def do_url_for_search_page(page):
    args = request.args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


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
    return iso8601.parse_date(s).strftime(format)


@app.template_filter('iso8601_delay_in_days')
def do_iso8601_delay_in_days(q, a=None):
    s = a or datetime.datetime.now().isoformat()
    delay = iso8601.parse_date(s) - iso8601.parse_date(q)
    return delay.days


@app.template_filter('nl2br')
def do_nl2br(s):
    return s.replace('\n', '<br>')


class BackendAPI(object):
    URL = 'http://c-tkv-nginx/v0'

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

    def search_questions(self, query=None, page=1):
        es_query = {
            "sort": "date",
            "order": "desc",
            "from": (page - 1) * PAGE_SIZE,
            "size": PAGE_SIZE
        }

        if query is not None:
            es_query['query'] = query

        try:
            result = requests.post(
                '%s/tk_qa_matches/search' % (self.URL,),
                data=json.dumps(es_query)).json()
        except Exception:
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
                "id": {"terms": [id]}
            },
            "size": 1
        }

        return requests.post(
            '%s/tk_qa_matches/search' % (self.URL,),
            data=json.dumps(es_query)).json()

api = BackendAPI()


@app.route("/")
def main():
    page = int(request.args.get('page', '1'))
    query = None
    results = api.search_questions(query, page)
    max_pages = int(math.ceil(results['meta']['total'] / PAGE_SIZE))
    today = datetime.datetime.now()
    stats = api.get_stats_in_period("%s-01-01T00:00:00" % (today.year,))
    return render_template(
        'index.html', results=results, stats=stats, query=query, page=page,
        max_pages=max_pages)


@app.route("/stats")
def stats():
    results = api.stats_questions()
    return render_template('stats.html', results=results)


@app.route("/zoeken")
def search():
    page = int(request.args.get('page', '1'))
    query = request.args.get('query', None)
    results = api.search_questions(query, page)
    max_pages = int(math.ceil(results['meta']['total'] / PAGE_SIZE))
    return render_template(
        'search_results.html', results=results, query=query, page=page,
        max_pages=max_pages)


@app.route("/<period>/<id>")
def display(period, id):
    result = api.find_by_id(id)

    if result['meta']['total'] <= 0:
        abort(404)

    return render_template(
        'display_result.html', result=result['hits']['hits'][0])


def create_app():
    return app
