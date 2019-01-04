from datetime import datetime
import sys

import iso8601

from lxml import etree

from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.items import BaseItem


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
            'source': unicode(
                self.source_definition.get('source', 'Partij nieuws')),
            'type': unicode(self.source_definition.get('type', 'Partij')),
            'parties': [unicode(self.source_definition['collection'])]
        }

        # TODO: provide easier way for default mapping
        mappings = {
            'summary': 'description'
        }
        mappings.update(self.source_definition.get('mappings', {}))

        for fld in ['title', 'summary']:
            if self.original_item.get(fld, None) is not None:
                mapping_fld = mappings.get(fld, fld)
                combined_index_data[mapping_fld] = self.original_item[fld]

        # try to get the full content, if available
        try:
            combined_index_data['description'] = self.original_item[
                'content'][0]['value']
        except LookupError:
                pass

        try:
            combined_index_data['date'] = iso8601.parse_date(
                self.original_item['published_parsed'])
        except LookupError:
            pass

        if self.source_definition.get('location', None) is not None:
            combined_index_data['location'] = unicode(self.source_definition[
                'location'].decode('utf-8'))
        combined_index_data['date_granularity'] = 12

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


class FeedPhantomJSItem(FeedItem):
    @property
    def driver(self):
        driver = getattr(self, '_driver', None)
        if not driver:
            self._driver = webdriver.Remote(
                command_executor='http://phantomjs:8910',
                desired_capabilities=DesiredCapabilities.PHANTOMJS)
        return self._driver

    def get_combined_index_data(self):
        combined_index_data = super(
            FeedPhantomJSItem, self).get_combined_index_data()

        self.driver.get(self.original_item['link'])

        with open('/opt/pfl/scripts/detect.js') as in_file:
            detect_js = in_file.read()

        detect_js += """
        window._html_output = '';

        // define
        (function() {
            var _detect = {
              'callbacks': {
              'finished': function (_result) { window._html_output = _result._html; },
             },
             'window': window,
             'jQuery': window.jQuery
            };
            _detect = initClearlyComponent__detect(_detect);
            _detect.start();
        })();
        """

        try:
            self.driver.execute_script(detect_js)
        except WebDriverException as e:
            pass

        # print driver.get_log('browser')

        output = self.driver.execute_script(
            'return window._html_output;')
        # self.driver.quit()

        if output.strip() != u'':
            combined_index_data['description'] = output

        return combined_index_data
