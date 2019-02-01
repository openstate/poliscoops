import sys
from datetime import datetime
import json
import re
from pprint import pprint
from urlparse import urljoin

from lxml import etree
from ocd_backend.items import BaseItem
from ocd_backend.extractors import HttpRequestMixin


class PVDDItem(BaseItem):
    def _get_text_or_none(self, xpath_expression):
        node = self.original_item.find(xpath_expression)
        if node is not None and node.text is not None:
            return unicode(node.text)

    def get_original_object_id(self):
        # Use slug as object id
        return unicode(
            self.original_item.xpath(
                ".//meta[@property='og:url']/@content"
            )[0].split('/')[-1]
        )

    def get_original_object_urls(self):
        url = unicode(
            self.original_item.xpath(".//meta[@property='og:url']/@content")[0]
        )

        return {
            'html': url
        }

    def get_rights(self):
        return u'Undefined'

    def get_collection(self):
        return u'Unknown'

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden'],
            'source': unicode(
                self.source_definition.get('source', 'Partij nieuws')),
            'type': unicode(self.source_definition.get('type', 'Partij')),
            'parties': [unicode(self.source_definition['collection'])]
        }

        main = self.original_item.xpath(".")[0]

        # title
        xpath_query = './/article/header/h1/text()|.//div[@class="page"]/div/h1/text()'
        if main.xpath(xpath_query):
            combined_index_data['title'] = unicode(main.xpath(xpath_query)[0])

        # date
        xpath_query = './/article/header/div[@class="pagedate"]//text()|.//div[@class="pagedate"]//text()'
        if main.xpath(xpath_query):
            raw_date = main.xpath(xpath_query)[0]

            raw_date = raw_date.replace(
                ' januari ', '-01-').replace(' februari ', '-02-').replace(
                ' maart ', '-03-').replace(' april ', '-04-').replace(
                ' mei ', '-05-').replace(' juni ', '-06-').replace(
                ' juli ', '-07-').replace(' augutus ', '-07-').replace(
                ' september ', '-09-').replace(' oktober ', '-10-').replace(
                ' november ', '-11-').replace(' december ', '-12-')

            pattern = '%d-%m-%y'
            if len(raw_date) == 10:
                pattern = '%d-%m-%Y'
            combined_index_data['date'] = datetime.strptime(raw_date, pattern)
            combined_index_data['date_granularity'] = 12

        # decription
        xpath_query = './/article/p//text()|.//div[contains(@class, "content-small")]//p//text()'
        if main.xpath(xpath_query):
            combined_index_data['description'] = unicode(' '.join(main.xpath(xpath_query)))

        # location
        if self.source_definition.get('location', None) is not None:
            combined_index_data['location'] = unicode(self.source_definition[
                'location'].decode('utf-8'))

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
