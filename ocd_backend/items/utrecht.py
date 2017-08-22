from datetime import datetime
from hashlib import sha1
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

    def _get_title(self):
        if self.original_item.xpath(".//meta[@property='og:title']/@content"):
            return unicode(
                self.original_item.xpath(
                    ".//meta[@property='og:title']/@content")[0])

    def _get_url(self):
        return unicode(self.original_item.xpath(
            ".//meta[@property='og:url']/@content")[0])

    def _get_basic_info(self):
        """
        Returns a tuple of id, status and title.
        """
        # Title
        wob_title = None
        wob_status = u''
        wob_id = None
        wob_title = self._get_title()

        if wob_title:
            wob_id, wob_status, actual_title = wob_title.split(
                u' ', 2)

            if not re.match('^\d{4}', wob_id):
                # Use slug as object id
                wob_id = unicode(self._get_url().split('/')[-2])
        return (wob_id, wob_status, wob_title,)

    def _get_hashed_id(self, wob_id):
        obj_id = u'%s:%s' % (self.source_definition['index_name'], wob_id,)
        return unicode(sha1(obj_id.decode('utf8')).hexdigest())

    def get_object_id(self):
        wob_id, wob_status, wob_title = self._get_basic_info()
        # Use slug as object id
        return self._get_hashed_id(wob_id)

    def get_original_object_id(self):
        wob_id, wob_status, wob_title = self._get_basic_info()
        # Use slug as object id
        return wob_id

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
        wob_id, wob_status, wob_title = self._get_basic_info()
        combined_index_data['title'] = wob_title
        if re.match('^\d{4}', wob_id):
            combined_index_data['id'] = self._get_hashed_id(wob_id)
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


class UtrechtCategoryItem(UtrechtItem):
    combined_index_fields = {
        'doc': dict
    }

    def _get_title(self):
        return self.original_item['title']

    def _get_url(self):
        return self.original_item['url']

    def get_original_object_urls(self):
        return {
            'html': self.original_item['url'],
            'alternate': (
                u'https://archief12.archiefweb.eu/archives/archiefweb/'
                u'%s/%s') % (
                    datetime.now().strftime('%Y%m%d%H%m%S'),
                    self.original_item['url'],)
        }

    def get_rights(self):
        return u'Undefined'

    def get_collection(self):
        return u'Utrecht'

    def get_combined_index_data(self):
        doc = {
            'doc': {
                'categories': self.original_item['categories']
            }
        }
        return doc


class UtrechtOverviewItem(BaseItem):
    pass
