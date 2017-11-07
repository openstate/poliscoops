#!/usr/bin/env python
from datetime import datetime
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
        return [{
            "id": "groenlinks_" + slug,
            "location": name,
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
            "file_url": os.path.join(link, 'rss.xml'),
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
