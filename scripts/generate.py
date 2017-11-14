#!/usr/bin/env python
from datetime import datetime
import csv
import codecs
import json
from glob import glob
import gzip
from hashlib import sha1
import os
import re
import requests
import sys
import time
from urlparse import urljoin
from pprint import pprint

import click
from click.core import Command
from click.decorators import _make_command

from lxml import etree
import requests


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


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


def _generate_for_pvdd(name):
    def _generate_for_pvdd_subsite(name, link):
        m = re.match(r'^https?\:\/\/w?w?w?\.?([^\.]+)', link)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None
        url = os.path.join(link, 'nieuws')
        return [{
            "id": "pvdd_" + slug,
            "location": unicode(name),
            "extractor": "ocd_backend.extractors.pvdd.PVDDExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.pvdd.PVDDItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "pvdd",
            "collection": "Partij voor de Dieren",
            "file_url": url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://gemeenten.partijvoordedieren.nl/over-de-gemeenteraadsfracties', verify=False)
    html = etree.HTML(resp.content)
    party_elems = html.xpath('//article/p//a')
    result = []
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('.//text()'))
        try:
            local_link = party_elem.xpath('./@href')[0]
        except LookupError:
            local_link = None
        if local_link is not None and not local_link.endswith('pdf'):
            result += _generate_for_pvdd_subsite(local_name, local_link)
    return result


def _generate_for_groenlinks(name):
    def _generate_for_groen_links_subsite(name, link):
        m = re.match(r'^https?\:\/\/w?w?w?\.?([^\.]+)', link)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None
        feed_url = os.path.join(link, 'rss.xml')
        try:
            requests.head(feed_url)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError
        ):
            feed_url = os.path.join(link, 'feed')
        return [{
            "id": "groenlinks_" + slug,
            "location": unicode(name),
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.feed.FeedItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "groenlinks",
            "collection": "GroenLinks",
            "file_url": feed_url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://groenlinks.nl/lokaal')
    html = etree.HTML(resp.content)
    party_elems = html.xpath(
        '//ul[@class="clearfix province-departments-list"]//li/a')
    result = []
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('.//text()'))
        try:
            local_link = party_elem.xpath('./@href')[0]
        except LookupError:
            local_link = None
        if local_link is not None:
            result += _generate_for_groen_links_subsite(local_name, local_link)
    return result


def _generate_for_cda(name):
    def _generate_for_cda_subsite(name, link):
        prefix = u'' if link.startswith('/') else '/'
        feed_url = u'%s%s%s%s' % (
            'https://www.cda.nl', prefix,  link, u'nieuws.rss',)
        try:
            slug = link.split('/')[-2].replace('-', '_')
        except LookupError:
            slug = u''
        return [{
            "id": u"cda_%s" % (slug,),
            "location": unicode(name),
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.feed.FeedItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "cda",
            "collection": "CDA",
            "file_url": feed_url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://www.cda.nl/partij/afdelingen/')
    html = etree.HTML(resp.content)
    party_elems = html.xpath(
        '//div[@class="panel-mainContent"]//select[@class="redirectSelect"]//option')
    result = []
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('.//text()')).strip()
        try:
            local_link = party_elem.xpath('./@value')[0]
        except LookupError:
            local_link = None
        if local_link is not None:
            result += _generate_for_cda_subsite(local_name, local_link)
    return result


def _generate_for_cu(name):
    def _generate_for_cu_subsite(name, link):
        m = re.match(r'^https?\:\/\/w?w?w?\.?([^\.]+)', link)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None

        resp = requests.get(link)
        html = etree.HTML(resp.content)
        feeds = html.xpath('//link[@type="application/rss+xml"]')

        result = []
        feed_idx = 0
        for feed in feeds:
            feed_idx += 1
            feed_url = u''.join(feed.xpath('./@href'))
            result.append({
                "id": u"cu_%s_%s" % (slug.replace('-', '_'), feed_idx,),
                "location": unicode(name),
                "extractor": "ocd_backend.extractors.feed.FeedExtractor",
                "transformer": "ocd_backend.transformers.BaseTransformer",
                "item": "ocd_backend.items.feed.FeedItem",
                "enrichers": [
                ],
                "loader": "ocd_backend.loaders.ElasticsearchLoader",
                "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
                "hidden": False,
                "index_name": "christenunie",
                "collection": "ChristenUnie",
                "file_url": feed_url,
                "keep_index_on_update": True
            })
        return result

    resp = requests.get('https://www.christenunie.nl/lokaal-en-provinciaal')
    html = etree.HTML(resp.content)
    party_elems = html.xpath(
        '//form[@name="formName2"]/select//option')
    result = []
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('.//text()')).strip()
        try:
            local_link = party_elem.xpath('./@value')[0]
        except LookupError:
            local_link = None
        if local_link is not None:
            result += _generate_for_cu_subsite(local_name, local_link)
    return result


def _generate_for_vvd(name):
    def _generate_for_vvd_subsite(name, feed_url, feed_idx):
        m = re.match(r'^https?\:\/\/w?w?w?\.?([^\.]+)', feed_url)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None

        result = []
        result.append({
            "id": u"vvd_%s_%s" % (slug.replace('-', '_'), feed_idx,),
            "location": unicode(name),
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.feed.FeedItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "vvd",
            "collection": "VVD",
            "file_url": feed_url,
            "keep_index_on_update": True
        })
        return result

    result = []

    session = requests.session()

    with open('vvd.txt') as IN:
        lines = list(UnicodeReader(IN))

        feed_idx = 0
        for line in lines:
            feed_idx += 1

            rss_url = 'http://' + line[0] + '/feeds/nieuws.rss'

            # Get name from CSV or website
            if len(line) == 3:
                name = line[2]
                if line[1]:
                    rss_url = 'http://' + line[0] + line[1]
            else:
                url = 'http://' + line[0]
                resp = session.get(url, verify=False)
                html = etree.HTML(resp.content)
                name = html.xpath('.//span[@class="site-logo__text"]/text()')[0]

            # Get RSS feed path from CSV or assume default '/feeds/nieuws.rss'
            if len(line) == 2:
                rss_url = 'http://' + line[0] + line[1]

            result += _generate_for_vvd_subsite(name, rss_url, feed_idx)
    return result


def _generate_for_d66(name):
    def _generate_for_d66_subsite(name, link):
        m = re.match(r'^w?w?w?\.?([^\.]+)', link.replace('http://', '').replace('https', ''))
        if m is not None:
            slug = m.group(1)
        else:
            slug = None

        feed_url = "%s/feed/" % (link,)
        return [{
            "id": u"d66_%s" % (slug.replace('-', '_'),),
            "location": unicode(name),
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.feed.FeedItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "d66",
            "collection": "D66",
            "file_url": feed_url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://d66.nl/partij/d66-het-land/')
    html = etree.HTML(resp.content)
    provinces = html.xpath('//a[@class="tile-thumb"]/@href')
    result = []
    for province in provinces:
        province_resp = requests.get(province)
        province_html = etree.HTML(province_resp.content)
        party_elems = province_html.xpath('//div[@id="rs-content"]//p/a')
        for party_elem in party_elems:
            local_name = u''.join(party_elem.xpath('.//text()')).strip()
            try:
                local_link = party_elem.xpath('./@href')[0]
            except LookupError:
                local_link = None
            if local_link is not None:
                result += _generate_for_d66_subsite(local_name, local_link)
    return result


def _generate_for_sp(name):
    def _generate_for_sp_subsite(name, link):
        m = re.match(r'^https?\:\/\/w?w?w?\.?([^\.]+)', link)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None
        feed_url = os.path.join(link, 'rss.xml')
        try:
            requests.head(feed_url)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError
        ):
            feed_url = os.path.join(link, 'feed')
        return [{
            "id": "sp_" + slug,
            "location": unicode(name).replace('SP ', ''),
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.feed.FeedItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "sp",
            "collection": "SP",
            "file_url": feed_url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://www.sp.nl/wij-sp/lokale-afdelingen')
    html = etree.HTML(resp.content)
    party_elems = html.xpath(
        '//ul[@class="afdelingen-overview"]//li/a')
    result = []
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('.//text()'))
        try:
            local_link = party_elem.xpath('./@href')[0]
        except LookupError:
            local_link = None
        if local_link is not None:
            result += _generate_for_sp_subsite(local_name, local_link)
    return result


def _generate_for_pvda(name):
    def _generate_for_pvda_subsite(name, link):
        m = re.match(r'^https?s?\:\/\/w?w?w?\.?([^\.]+)', link)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None
        feed_url = os.path.join(link, 'feed')
        return [{
            "id": "pvda_" + slug,
            "location": unicode(name),
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.feed.FeedItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "pvda",
            "collection": "PvdA",
            "file_url": feed_url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://www.pvda.nl/partij/organisatie/lokale-afdelingen/')
    html = etree.HTML(resp.content)
    party_elems = html.xpath(
        '//select//option')
    result = []
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('.//text()'))
        try:
            local_link = party_elem.xpath('./@value')[0]
        except LookupError:
            local_link = None
        if local_link is not None:
            result += _generate_for_pvda_subsite(local_name, local_link)
    return result


def _generate_for_sgp(name):
    def _generate_for_sgp_subsite(name, link):
        if ".sgp.nl" not in link:
            return []

        m = re.match(r'^https?s?\:\/\/w?w?w?\.?([^\.]+)', link)
        if m is not None:
            slug = m.group(1)
        else:
            slug = None

        if slug is None:
            return []

        feed_url = u"%s/actueel" % (link,)
        try:
            requests.head(feed_url)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError
        ):
            feed_url = None

        if feed_url is None:
            return []

        return [{
            "id": "sgp_" + slug,
            "location": unicode(name).strip(),
            "extractor": "ocd_backend.extractors.staticfile.StaticHtmlExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.sgp.SGPItem",
            "enrichers": [
            ],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "sgp",
            "collection": "SGP",
            "item_xpath": "//a[contains(@class, \"overlay-link\")]",
            "file_url": feed_url,
            "keep_index_on_update": True
        }]

    resp = requests.get('https://www.sgp.nl/decentraal')
    html = etree.HTML(resp.content)
    party_elems = html.xpath(
        '//div[@class="markers"]//div')
    result = []
    links = {}
    for party_elem in party_elems:
        local_name = u''.join(party_elem.xpath('./h3//text()'))
        try:
            local_link = party_elem.xpath('.//a/@href')[0]
        except LookupError:
            local_link = None
        if (local_link is not None) and (links.get(local_link, None) is None):
            links[local_link] = 1
            result += _generate_for_sgp_subsite(local_name, local_link)
    return result


class SimpleFacebookAPI(object):
    def __init__(self, api_version, app_id, app_secret):
        self.api_version = api_version
        self.app_id = app_id
        self.app_secret = app_secret

    def _fb_get_access_token(self):
        return u"%s|%s" % (self.app_id, self.app_secret,)

    def _fb_search(self, query, next_url=None):
        if next_url is not None:
            graph_url = next_url
        else:
            graph_url = "https://graph.facebook.com/%s/search?q=%s&type=page&fields=id,location,name,username,website&access_token=%s" % (
                self.api_version, query,
                self._fb_get_access_token(),)
        r = requests.get(graph_url)
        r.raise_for_status()
        return r.json()

    def search(self, query):
        do_paging = True
        obj = self._fb_search(query)
        for item in obj['data']:
            yield item
        while do_paging and ('paging' in obj) and ('next' in obj['paging']):
            obj = self._fb_search(query, obj['paging']['next'])
            for item in obj['data']:
                yield item


def _generate_facebook_for_party(
    result, index_name, collection, replacements=[]
):
    slug = result.get('username', result['id'])
    if 'location' in result and 'city' in result['location']:
        location = result['location']['city']
    else:
        rep = {}  # define desired replacements here
        for replacement in replacements:
            rep[replacement] = u''
        # use these three lines to do the replacement
        rep = dict((re.escape(k), v) for k, v in rep.iteritems())
        pattern = re.compile("|".join(rep.keys()))
        location = pattern.sub(
            lambda m: rep[re.escape(m.group(0))], result['name'])
        location = location.strip()
    return [{
        "extractor": "ocd_backend.extractors.facebook.FacebookExtractor",
        "keep_index_on_update": True,
        "enrichers": [],
        "index_name": index_name,
        "collection": collection,
        "loader": "ocd_backend.loaders.ElasticsearchLoader",
        "id": "%s_fb_%s" % (index_name, slug,),
        "transformer": "ocd_backend.transformers.BaseTransformer",
        "facebook": {
          "api_version": os.environ['FACEBOOK_API_VERSION'],
          "app_id": os.environ['FACEBOOK_APP_ID'],
          "app_secret": os.environ['FACEBOOK_APP_SECRET'],
          "graph_url": "%s/feed" % (slug,),
          "paging": False
        },
        "item": "ocd_backend.items.facebook.PageItem",
        "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
        "location": location,
        "hidden": False
    }]


def _generate_fb_for_groenlinks(name):

    api = SimpleFacebookAPI(
        os.environ['FACEBOOK_API_VERSION'], os.environ['FACEBOOK_APP_ID'],
        os.environ['FACEBOOK_APP_SECRET'])
    result = api.search('GroenLinks')
    return [
        _generate_facebook_for_party(
            r, 'groenlinks', 'GroenLinks',
            [
                'GroenLinks', 'Groen Links', 'Groenlinks', 'GROENLINKS',
                '/pe', 'Groen & Sociaal'
            ]
        ) for r in result
        if ('.groenlinks.nl' in r.get('website', '')) and
        r.get('name', '').lower().startswith('groen')
    ]


@click.group()
@click.version_option()
def cli():
    """Poliflw"""


@cli.group()
def sources():
    """Generate sources for a party"""


@command('party')
@click.argument('name', default='')
def generate_sources_local_party(name):
    """
    This generate the sources for a party

    param: name: The name of the party
    """

    method_name = '_generate_for_%s' % (name,)
    possibles = globals().copy()
    possibles.update(locals())
    method = possibles.get(method_name)

    sources = (
        method(name)
    )

    print json.dumps(sources, indent=4)


@command('facebook')
@click.argument('name', default='')
def generate_facebook_local_party(name):
    """
    This generate the facebook sources for a party

    param: name: The name of the party
    """

    method_name = '_generate_fb_for_%s' % (name,)
    possibles = globals().copy()
    possibles.update(locals())
    method = possibles.get(method_name)

    sources = (
        method(name)
    )

    print json.dumps(sources, indent=4)

sources.add_command(generate_sources_local_party)
sources.add_command(generate_facebook_local_party)

if __name__ == '__main__':
    cli()
