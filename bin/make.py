#!/usr/bin/env python

import os
import sys
import json
import csv
from urlparse import urljoin
import re
from time import sleep

import click
from click.core import Command
from click.decorators import _make_command

from jparser import PageModel
from elasticsearch import Elasticsearch
from lxml import etree
import requests
import feedparser

sys.path.insert(0, '.')
from ocd_backend.utils.misc import slugify


def command(name=None, cls=None, **attrs):
    """
    Wrapper for click Commands, to replace the click.Command docstring with the
    docstring of the wrapped method (i.e. the methods defined below). This is
    done to support the autodoc in Sphinx, and the correct display of
    docstrings
    """
    if cls is None:
        cls = Command

    def decorator(f):
        r = _make_command(f, name, attrs, cls)
        r.__doc__ = f.__doc__
        return r
    return decorator


def get_facebook_path(full_url):
    parts = full_url.replace(
        "https://www.facebook.com/", "").split("/")
    first_part = parts[0]
    if first_part in ['groups', 'pages']:
        return "%s/%s" % (parts[0], parts[1],)
    else:
        return first_part


def get_content_from_page(page_url):
    r = requests.get(page_url, timeout=5)

    # only continue if we got the page
    if r.status_code < 200 or r.status_code >= 300:
        return u''

    try:
        full_content = r.content
    except etree.ElementTree.ParseError as e:
        return u''
    return clean_content(full_content, r.encoding)


def clean_content(full_content, encoding='utf-8'):
    # TODO: Fix byte 0xff problem: 'utf8' codec can't decode byte 0xff in position <x>: invalid start byte
    # TODO: Fix Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
    # TODO: remove things like: Share on Facebook Share Share on Twitter Tweet Share on Pinterest Share Share on LinkedIn Share Send email Mail Print Print
    try:
        cleaned = PageModel(full_content.decode(encoding)).extract()
    except Exception as e:
        print >>sys.stderr, e
        cleaned = {}

    output = u''
    for elem in cleaned.get('content', []):
        if elem['type'] == 'text':
            # if it starts with these words it's probably garbage
            if re.match('^\s*(Share|Deel|Delen|Send|Print)\s*', elem['data']) is None:
                output += '%s\n' % (elem['data'],)
        # if elem['type'] == 'image':
        #     output += '<img src="%s" />' % (elem['data']['src'],)

    if output.strip() != u'':
        return unicode(output)
    return u''


def get_item_transformer_for_feed(feed_url):
    feed = feedparser.parse(feed_url)
    len_feed = 0
    len_page = 0
    max_entries = 3
    num_entries = 0
    for entry in feed.entries:
        if num_entries >= max_entries:
            continue
        num_entries += 1
        try:
            clean_desc = clean_content(entry.description).strip()
        except Exception as e:
            clean_desc = u''
        try:
            clean_page = get_content_from_page(entry.link).strip()
        except Exception as e:
            clean_page = u''
        # print "Feed:\n\n"
        # print clean_desc
        # print "\n\nPage:\n\n"
        # print clean_page
        if clean_desc != clean_page:
            len_feed += len(clean_desc)
            len_page += len(clean_page)
        sleep(1)


    if len_page > len_feed:
        return "ocd_backend.items.feed.FeedContentFromPageItem"
    return "ocd_backend.items.feed.FeedItem"


def get_source_info_from_url(file_url):
    result = {
        'extractor': "ocd_backend.extractors.linkmap.LinkmapExtractor",
        'item': "ocd_backend.items.html.HTMLWithContentOnPageItem"
    }

    try:
        req_res = requests.get(file_url)
        content = req_res.content
    except Exception as e:
        print(e)
        raise

    res = feedparser.parse(content)

    if len(res.entries) > 0:  # this is an RSS feed
        result['file_url'] = file_url
        result['extractor'] = "ocd_backend.extractors.feed.FeedExtractor"
        result['item'] = get_item_transformer_for_feed(result['file_url'])
        return result

    # parse the html and try to find the link to the RSS feed
    try:
        html = etree.HTML(content)
    except Exception as e:
        html = None

    if html is not None:
        try:
            feed_link = html.xpath('//link[@rel="alternate" and (@type="application/atom+xml" or @type="application/rss+xml")]/@href')[0]
        except Exception as e:
            feed_link = None

        if feed_link is not None:
            result['file_url'] = urljoin(file_url, feed_link)
            result['extractor'] = "ocd_backend.extractors.feed.FeedExtractor"
            result['item'] = get_item_transformer_for_feed(result['file_url'])
            return result

    # Fallback options
    result['file_url'] = file_url
    return result


def is_facebook(url):
    if url is not None:
        return (re.search('\.facebook.com\/', url) is not None)
    return False


def make_source_for(src, LOCATIONS):
    slug = slugify(src['collection']).replace('-', '_')
    slug_location = slugify(src['location'])

    if is_facebook(src['file_url']):
        feed_id = "%s_%s_fb_1" % (slug, slug_location,)
    else:
        feed_id = "%s_%s_1" % (slug, slug_location,)

    result = {
        "extractor": "",  # depends if feed or not
        "keep_index_on_update": True,
        "enrichers": [
          # [
          #   "ocd_backend.enrichers.NEREnricher",
          #   {}
          # ],
          # [
          #   "ocd_backend.enrichers.BinoasEnricher",
          #   {}
          # ]
        ],
        "file_url": '',
        "index_name": slug,
        "transformer": "ocd_backend.transformers.BaseTransformer",
        "loader": "ocd_backend.loaders.ElasticsearchLoader",
        "item": "",  # html grabber
        "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
        "location": _normalize_location(src['location'], LOCATIONS),
        "hidden": False,
        "id": feed_id
    }

    if not is_facebook(src['file_url']):
        additional = get_source_info_from_url(src['file_url'])
        for k, v in additional.iteritems():
            result[k] = v
    else:
        result["extractor"] = "ocd_backend.extractors.facebook.FacebookExtractor"
        result["item"] = "ocd_backend.items.facebook.PageItem"
        result["facebook"] = {
            'app_secret': os.environ.get('FACEBOOK_APP_SECRET', None),
            'app_id': os.environ.get('FACEBOOK_APP_ID', None),
            "paging": False,
            "api_version": "v2.11",
            "graph_url": "%s/posts" % (
                get_facebook_path(src['file_url']),)
        }

    for k, v in src.iteritems():
        if k != 'file_url':
            result[k] = v
    return result


def make_sources_for(srcs):
    LOCATIONS = _get_normalized_locations()

    sources = [make_source_for(src, LOCATIONS) for src in srcs if src['file_url'] is not None]
    return json.dumps(sources, indent=4)


def _get_normalized_locations():
    loc_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        '/opt/pfl/ocd_backend/data/cbs-name2018-mapping.csv')
    result = {}
    with open(loc_path) as locations_in:
        locations = reader = csv.reader(locations_in)
        headers = locations.next()
        for location in locations:
            record = dict(zip(headers, location))
            result[record[u'Key_poliflw']] = record[u'Alt_map']
    return result


def _normalize_location(location, LOCATIONS):
    if unicode(location) in LOCATIONS:
        return LOCATIONS[unicode(location)]
    return unicode(location)


@click.group()
@click.version_option()
def cli():
    """Poliflw"""


@cli.group()
def sources():
    """Generate sources for a link or list of links"""


@command('list')
@click.argument('file')
def generate_source_from_file(file):
    """
    This generate the sources for a list of urls in a JSON file

    param: name: The name of the party
    """

    srcs = []
    with open(file) as in_file:
        srcs = json.load(in_file)
    print make_sources_for(srcs)

sources.add_command(generate_source_from_file)

if __name__ == '__main__':
    cli()
