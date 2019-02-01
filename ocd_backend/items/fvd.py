from datetime import datetime
import sys
import re

import iso8601

from lxml import etree

from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.items import BaseItem
from ocd_backend.utils.misc import html_cleanup, html_cleanup_with_structure


class FVDItem(BaseItem, HttpRequestMixin):
    def get_original_object_id(self):
        return unicode(self.original_item['slug'])

    def get_original_object_urls(self):
        return {
            'html': 'https://forumvoordemocratie.nl/actueel/%s' % (
                self.original_item['slug'],)
        }

    def get_rights(self):
        return unicode(self.original_item.get('rights', 'Undefined'))

    def get_collection(self):
        return unicode(self.source_definition.get('collection', 'Unknown'))

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden'],
            'source': unicode(
                self.source_definition.get('source', 'Partij nieuws')),
            'type': unicode(self.source_definition.get('type', 'Partij')),
            'parties': [unicode(self.source_definition['collection'])]
        }

        detail_link = 'https://forumvoordemocratie.nl/api/articles/details/%s' % (
            self.original_item['slug'],)
        r = self.http_session.get(detail_link)
        print >>sys.stderr, "Got %s with status code : %s" % (
            detail_link, r.status_code)

        detail = {}
        # only continue if we got the page
        if r.status_code >= 200 or r.status_code < 300:
            detail = r.json()

        combined_index_data['title'] = unicode(self.original_item['title'])

        try:
            combined_index_data['description'] = unicode(detail['content'])
        except Exception as e:
            combined_index_data['description'] = unicode(
                self.original_item['summary'])

        try:
            combined_index_data['date'] = iso8601.parse_date(
                self.original_item['publishedAt'])
        except LookupError:
            pass

        if self.original_item['creator'].startswith('FVD'):
            combined_index_data['location'] = unicode(
                self.original_item['creator'].replace('FVD', '').strip())
            if combined_index_data['location'].strip() == u'':
                combined_index_data['location'] = unicode(
                    self.source_definition['location'])
        else:
            combined_index_data['location'] = unicode(
                self.source_definition['location'])

        combined_index_data['date_granularity'] = 12

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
