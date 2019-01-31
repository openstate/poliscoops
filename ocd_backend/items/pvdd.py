from datetime import datetime
import json
import re

from lxml import etree
from ocd_backend.items import BaseItem


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

        self.original_item.xpath('.//article/header/h1')

        # title
        xpath_query = './/article/header/h1/text()'
        if main.xpath(xpath_query):
            combined_index_data['title'] = unicode(main.xpath(xpath_query)[0])

        # date
        xpath_query = './/article/header/div[@class="date"]//text()'
        if main.xpath(xpath_query):
            raw_date = main.xpath(xpath_query)[0]
            pattern = '%d-%m-%y'
            if len(raw_date) == 10:
                pattern = '%d-%m-%Y'
            combined_index_data['date'] = datetime.strptime(raw_date, pattern)
            combined_index_data['date_granularity'] = 12

        # decription
        xpath_query = './/article/p//text()'
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


class PVDDFromPageItem(PVDDItem):
    def get_combined_index_data(self):
        link = self.original_item.xpath('.//a/@href')[0]
        r = self.http_session.get(link, timeout=5)
        print >>sys.stderr, "Got %s with status code : %s" % (
            link, r.status_code)

        # only continue if we got the page
        if r.status_code >= 200 or r.status_code < 300:
            try:
                self.original_item = etree.HTML(r.content)
            except Exception:
                pass

        return super(PVDDFromPageItem, self).get_combined_index_data()
