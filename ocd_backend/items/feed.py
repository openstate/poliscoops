from datetime import datetime
import sys
import re

import iso8601

from lxml import etree

from jparser import PageModel

from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.items import BaseItem
from ocd_backend.utils.misc import html_cleanup, html_cleanup_with_structure
from ocd_backend.utils.html import HTMLContentExtractionMixin

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import WebDriverException


class FeedItem(BaseItem):
    def get_original_object_id(self):
        return unicode(self.original_item['link'])

    def get_original_object_urls(self):
        return {
            'html': self.original_item['link']
        }

    def get_rights(self):
        return unicode(self.original_item.get('rights', 'Undefined'))

    def get_collection(self):
        return unicode(self.source_definition.get('collection', 'Unknown'))

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden'],
            # 'source': unicode(
            #     self.source_definition.get('source', 'Partij nieuws')),
            # 'type': unicode(self.source_definition.get('type', 'Partij')),
            # 'parties': [unicode(self.source_definition['collection'])]
        }
        combined_index_data['item'] = {
            "@type": "Create",
            "actor": {
                "@type": u"Organization",
                "name": unicode(self.source_definition['collection']),
                "@id": "https://www.poliflw.nl/ns/#%s" % (
                    unicode(self.source_definition['collection']))
            },
            "object": {
                "@type": "Note",
                "name": self.original_item['title'],
                "@id": unicode(self.original_item['link'])
            },
            "@context": "http://www.w3.org/ns/activitystreams"
        }
        # TODO: provide easier way for default mapping
        # mappings = {
        #     'summary': 'description'
        # }
        # mappings.update(self.source_definition.get('mappings', {}))
        #
        # for fld in ['title', 'summary']:
        #     if self.original_item.get(fld, None) is not None:
        #         mapping_fld = mappings.get(fld, fld)
        #         combined_index_data[mapping_fld] = self.original_item[fld]
        #
        # # try to get the full content, if available
        # try:
        #     combined_index_data['description'] = self.original_item[
        #         'content'][0]['value']
        # except LookupError:
        #         pass
        #
        # try:
        #     combined_index_data['date'] = iso8601.parse_date(
        #         self.original_item['published_parsed'])
        # except LookupError:
        #     pass
        #
        # if self.source_definition.get('location', None) is not None:
        #     combined_index_data['location'] = unicode(self.source_definition[
        #         'location'].decode('utf-8'))
        # combined_index_data['date_granularity'] = 12

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)


class FeedFullTextItem(FeedItem, HttpRequestMixin):
    def get_combined_index_data(self):
        combined_index_data = super(
            FeedFullTextItem, self).get_combined_index_data()

        r = self.http_session.get(self.original_item['link'])
        print >>sys.stderr, "Got %s with status code : %s" % (
            self.original_item['link'], r.status_code)

        # only continue if we got the page
        if r.status_code < 200 or r.status_code >= 300:
            return combined_index_data

        try:
            html = etree.HTML(r.content)
        except etree.ElementTree.ParseError as e:
            return combined_index_data

        output = u''
        for elem in html.xpath(self.source_definition['content_xpath']):
            output += unicode(etree.tostring(elem))

        if output.strip() != u'':
            combined_index_data['description'] = output

        return combined_index_data


class FeedContentFromPageItem(FeedItem, HttpRequestMixin, HTMLContentExtractionMixin):
    def get_combined_index_data(self):
        combined_index_data = super(
            FeedContentFromPageItem, self).get_combined_index_data()

        r = self.http_session.get(self.original_item['link'], timeout=5)
        print >>sys.stderr, "Got %s with status code : %s" % (
            self.original_item['link'], r.status_code)

        # only continue if we got the page
        if r.status_code < 200 or r.status_code >= 300:
            return combined_index_data

        try:
            full_content = r.content
        except etree.ElementTree.ParseError as e:
            return combined_index_data

        desc = self.extract_content(full_content, r.encoding)
        if desc is not None:
            combined_index_data['description'] = unicode(output)

        return combined_index_data
