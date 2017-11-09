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

sources.add_command(generate_sources_local_party)

if __name__ == '__main__':
    cli()
