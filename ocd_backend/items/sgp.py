from datetime import datetime
import os
from urlparse import urlparse

import iso8601
import requests
from lxml import etree

from ocd_backend.items import BaseItem


class SGPItem(BaseItem):
    def get_original_object_id(self):
        url_info = urlparse(self.source_definition['file_url'])
        base_href = u'%s://%s' % (url_info.scheme, url_info.netloc,)
        return unicode(os.path.join(
            base_href,
            u''.join(self.original_item.xpath('//@href'))))

    def get_original_object_urls(self):
        url_info = urlparse(self.source_definition['file_url'])
        base_href = u'%s://%s' % (url_info.scheme, url_info.netloc,)
        return {
            'html': unicode(os.path.join(
                base_href,
                u''.join(self.original_item.xpath('//@href'))))
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

        url_info = urlparse(self.source_definition['file_url'])
        base_href = u'%s://%s' % (url_info.scheme, url_info.netloc,)
        resp = requests.get(unicode(os.path.join(
            base_href,
            u''.join(self.original_item.xpath('//@href')))))
        html = etree.HTML(resp.content)

        combined_index_data['title'] = u''.join(html.xpath('//h1//text()'))

        try:
            combined_index_data['description'] = unicode(etree.tostring(
                    html.xpath('//div[contains(@class, "text")]')[0])).strip()
        except LookupError:
            print "No text for URL %s" % (resp.url,)

        try:
            datum_orig = unicode(
                html.xpath('//span[@class="date"]//text()')[0])
            datum_as_string = datum_orig.replace('Publicatiedatum: ', '').replace(
                ' jan. ', '-01-').replace(' feb. ', '-02-').replace(
                ' mar. ', '-03-').replace(' apr. ', '-04-').replace(
                ' mei ', '-05-').replace(' jun. ', '-06-').replace(
                ' jul. ', '-07-').replace(' aug. ', '-07-').replace(
                ' sep. ', '-09-').replace(' okt. ', '-10-').replace(
                ' nov. ', '-11-').replace(' dec. ', '-12-')
            prefix = u'' if not datum_as_string.startswith('0') else u'0'
            combined_index_data['date'] = datetime.strptime(
                '%s%s' % (prefix, datum_as_string,), '%d-%m-%Y')
        except (ValueError, LookupError):
            pass

        combined_index_data['date_granularity'] = 12

        if self.source_definition.get('location', None) is not None:
            combined_index_data['location'] = unicode(self.source_definition[
                'location'])

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
