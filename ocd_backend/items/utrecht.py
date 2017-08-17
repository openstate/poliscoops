from datetime import datetime
import re

from ocd_backend.items import BaseItem


class UtrechtItem(BaseItem):
    combined_index_fields = {
        'hidden': bool,
        'title': unicode,
        'description': unicode,
        'date': datetime,
        'date_granularity': int,
        'authors': list,
        'media_urls': list,
        'all_text': unicode,
        'id': unicode,
        'status': unicode,
        'categories': list
    }

    def _get_text_or_none(self, xpath_expression):
        node = self.original_item.find(xpath_expression)
        if node is not None and node.text is not None:
            return unicode(node.text)

    def get_original_object_id(self):
        # Use slug as object id
        return unicode(
            self.original_item.xpath(".//meta[@property='og:url']/@content")[
                0].split('/')[-2])

    def get_original_object_urls(self):
        url = unicode(
            self.original_item.xpath(".//meta[@property='og:url']/@content")[0]
        )

        # Check if we are dealing with an archived page, if true then
        # prepend the archive URL to the original URL
        archive_url = unicode(
            self.original_item.xpath(".//link[@rel='stylesheet']/@href")[
                -1].split('http')[1])

        if 'archiefweb.eu' in archive_url:
            url = u'http' + archive_url + url

        if self.original_item.xpath(".//time/@datetime"):
            item_date = datetime.strptime(
                self.original_item.xpath(".//time/@datetime")[0],
                '%Y-%m-%dT%H:%M'
            )
        else:
            item_date = datetime.datetime.now()

        return {
            'html': url,
            'alternate': (
                u'https://archief12.archiefweb.eu/archives/archiefweb/'
                u'%s/%s') % (item_date.strftime('%Y%m%d%H%m%S'), url,)
        }

    def get_rights(self):
        return u'Undefined'

    def get_collection(self):
        return u'Utrecht'

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden']
        }

        # Title
        if self.original_item.xpath(".//meta[@property='og:title']/@content"):
            combined_index_data['title'] = unicode(
                self.original_item.xpath(
                    ".//meta[@property='og:title']/@content")[0])

        wob_id, wob_status, actual_title = combined_index_data['title'].split(
            u' ', 2)

        if re.match('^\d{4}', wob_id):
            combined_index_data['id'] = wob_id
            combined_index_data['status'] = wob_status

        # Description
        # Case for new website design
        if self.original_item.xpath("(.//div[@class='limiter']/p)[1]//text()"):
            combined_index_data['description'] = unicode(
                ''.join(
                    self.original_item.xpath(
                        "(.//div[@class='limiter']/p)[1]//text()")))

        # Case for old website design
        elif self.original_item.xpath(
            "(.//div[@class='news-single-item']/p)[1]//text()"
        ):
            combined_index_data['description'] = unicode(
                ''.join(self.original_item.xpath(
                    "(.//div[@class='news-single-item']/p)[1]//text()")))

        # Date
        if self.original_item.xpath(".//time/@datetime"):
            combined_index_data['date'] = datetime.strptime(
                self.original_item.xpath(".//time/@datetime")[0],
                '%Y-%m-%dT%H:%M'
            )
            combined_index_data['date_granularity'] = 12

        # media urls
        combined_index_data['media_urls'] = []
        for u in self.original_item.xpath(".//a[@class='download']/@href"):
            actual_url = unicode(u)
            if actual_url.startswith(u'/'):
                actual_url = u'https://www.utrecht.nl%s' % (actual_url,)
            combined_index_data['media_urls'].append({
                'original_url': actual_url,
                'content_type': u'application/pdf'
            })

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
