from datetime import datetime
import sys
import re

import iso8601

from lxml import etree

from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.items import BaseItem
from ocd_backend.utils.html import HTMLContentExtractionMixin
from ocd_backend.utils.voc import VocabularyMixin


class HTMLPageItem(BaseItem, HttpRequestMixin, VocabularyMixin):
    def _get_orig_link(self):
        return unicode(self.original_item['link'])

    def get_original_object_id(self):
        return unicode(self.original_item['link'])

    def get_original_object_urls(self):
        return {
            'html': unicode(self.original_item['link'])
        }

    def get_rights(self):
        return unicode(self.source_definition.get('rights', 'Undefined'))

    def get_collection(self):
        return unicode(self.source_definition.get('collection', 'Unknown'))

    def _extract_content(self, html=None, encoding=None):
        output = u''
        for elem in html.xpath(self.source_definition['content_xpath']):
            output += unicode(etree.tostring(elem))
        return output

    def _extract_title(self, html=None):
        return u''.join(html.xpath(
            self.source_definition['title_xpath']))

    def _extract_date(self, html=None):
        parsed_date = None
        parsed_granularity = None

        # assumes text
        date_str = u''.join(html.xpath(self.source_definition['date_xpath']))
        date_match = re.search((
            r'(\d+)\s+(januari|februari|maart|april|mei|juni|juli|augustus|'
            r'september|oktober|november|december)\s+(\d{4})'), date_str)
        if not date_match:
            date_match = re.search((
                r'(\d+)\s+(jan\.|feb\.|mar\.|apr\.|mei|jun\.|jul\.|aug\.|'
                r'sep\.|okt\.|nov\.|dec\.)\s+(\d{4})'), date_str)
        if date_match is not None:
            date_conversions = {
                'januari': '01', 'februari': '02', 'maart': '03',
                'april': '04', 'mei': '05', 'juni': '06', 'juli': '07',
                'augustus': '08', 'september': '09', 'oktober': '10',
                'november': '11', 'december': '12', 'jan.': '01',
                'feb.': '02', 'mar.': '03', 'apr.': '04', 'mei': '05',
                'jun.': '06', 'jul.': '07', 'aug.': '08', 'sep.': '09',
                'okt.': '10', 'nov.': '11', 'dec.': '12'}
            if len(date_match.group(1)) <= 1:
                date_prefix = '' if date_match.group(1).startswith('0') else '0'
            else:
                date_prefix = ''
            date_semi_parsed = u'%s-%s-%s%sT00:00:00' % (
                date_match.group(3), date_conversions[date_match.group(2)],
                date_prefix, date_match.group(1),)
            try:
                parsed_date = iso8601.parse_date(
                    date_semi_parsed)
                parsed_granularity = 12
            except LookupError:
                pass
        return parsed_date, parsed_granularity

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden'],
            'source': unicode(
                self.source_definition.get('source', 'Partij nieuws')),
            'type': unicode(self.source_definition.get('type', 'Partij')),
            'parties': [unicode(self.source_definition['collection'])]
        }

        orig_link = self._get_orig_link()
        r = self.http_session.get(orig_link)
        print >>sys.stderr, "Got %s with status code : %s" % (
            orig_link, r.status_code)

        # only continue if we got the page
        if r.status_code < 200 or r.status_code >= 300:
            return combined_index_data

        try:
            html = etree.HTML(r.content)
        except etree.ElementTree.ParseError:
            return combined_index_data

        output = self._extract_content(html, r.encoding)

        if output.strip() != u'':
            combined_index_data['description'] = output

        combined_index_data['title'] = self._extract_title(html)

        combined_index_data['date'], combined_index_data['date_granularity'] = self._extract_date(html)

        if self.source_definition.get('location', None) is not None:
            combined_index_data['location'] = unicode(self.source_definition[
                'location'].decode('utf-8'))

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)


class HTMLWithContentOnPageItem(HTMLPageItem, HTMLContentExtractionMixin):
    def _extract_content(self, html=None, encoding=None):
        return self.extract_content(etree.tostring(html), encoding)

    def _extract_title(self, html=None):
        return u''.join(html.xpath('//title[0]/text()'))

    def _extract_date(self, html=None):
        parsed_date = datetime.now()
        parsed_granularity = 12
        return parsed_date, parsed_granularity
