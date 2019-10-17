import datetime
import hashlib
import json
import os
import os.path
import time
from urlparse import urljoin, urlparse

import requests
from lxml import etree

from ocd_backend.settings import LINKMAP_PATH

def get_news_page_url_hash(news_page_url):
    return hashlib.sha224(news_page_url).hexdigest()

def get_news_page_url_path(news_page_url):
    return os.path.join(LINKMAP_PATH, '%s.linkmap' % (get_news_page_url_hash(news_page_url,)))

def is_internal_link(l, news_page_url):
    # TODO: can be the full url is hardcoded
    # see https://stackoverflow.com/questions/32314304/check-if-an-url-is-relative-to-another-ie-they-are-on-the-same-host
    return not (
        # (urljoin(news_page_url, l) == l) or
        l.startswith('http') or
        l.startswith('javascript:') or
        l.endswith('.css') or
        l.endswith('.js')
    )

def normalize_url(base_url, link):
    u = urlparse(urljoin(base_url, link))
    return u.geturl().replace('#' + u.fragment, '')

def build_linkmap(news_page_url, html):
    """
    Builds a link map from HTML parse by etree.
    """
    links = [normalize_url(news_page_url, l) for l in html.xpath('//a/@href') if is_internal_link(l, news_page_url)]
    return {
        'meta': {
            'version': '1',
            'generated': time.mktime(datetime.datetime.now().timetuple()),
            'url': news_page_url,
            'file': get_news_page_url_path(news_page_url)
        },
        'links': links,
        'yielded': []
    }

def save_linkmap(news_page_url, linkmap):
    with open(get_news_page_url_path(news_page_url), 'w') as out_file:
        json.dump(linkmap, out_file)

def load_linkmap(news_page_url):
    result = None
    try:
        with open(get_news_page_url_path(news_page_url)) as in_file:
            result = json.load(in_file)
    except IOError as e:
        pass
    return result
