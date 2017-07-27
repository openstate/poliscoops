from datetime import datetime
from lxml import etree

from ocd_backend.items import BaseItem

class UtrechtItem(BaseItem):
    def _get_text_or_none(self, xpath_expression):
        node = self.original_item.find(xpath_expression)
        if node is not None and node.text is not None:
            return unicode(node.text)

    def get_original_object_id(self):
        # Use slug as object id
        return unicode(self.original_item.xpath(".//meta[@property='og:url']/@content")[0].split('/')[-2])

    def get_original_object_urls(self):
        url = unicode(self.original_item.xpath(".//meta[@property='og:url']/@content")[0])

        # Check if we are dealing with an archived page, if true then
        # prepend the archive URL to the original URL
        archive_url = unicode(self.original_item.xpath(".//link[@rel='stylesheet']/@href")[-1].split('http')[1])
        if 'archiefweb.eu' in archive_url:
            url = u'http' + archive_url + url

        return {
            'html': url
        }

    def get_rights(self):
        return u'Undefined'

    def get_collection(self):
        return u'Utrecht'

    def get_combined_index_data(self):
        combined_index_data = {}

        # Title
        if self.original_item.xpath(".//meta[@property='og:title']/@content"):
            combined_index_data['title'] = unicode(self.original_item.xpath(".//meta[@property='og:title']/@content")[0])

        # Description
        # Case for new website design
        if self.original_item.xpath("(.//div[@class='limiter']/p)[1]//text()"):
            combined_index_data['description'] = unicode(''.join(self.original_item.xpath("(.//div[@class='limiter']/p)[1]//text()")))
        # Case for old website design
        elif self.original_item.xpath("(.//div[@class='news-single-item']/p)[1]//text()"):
            combined_index_data['description'] = unicode(''.join(self.original_item.xpath("(.//div[@class='news-single-item']/p)[1]//text()")))

        # Date
        if self.original_item.xpath(".//time/@datetime"):
            combined_index_data['date'] = datetime.strptime(
                self.original_item.xpath(".//time/@datetime")[0],
                '%Y-%m-%dT%H:%M'
            )
            combined_index_data['date_granularity'] = 12

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
