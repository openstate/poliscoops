from datetime import datetime
import sys
import re

import iso8601

from lxml import etree

from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.items import BaseItem
from ocd_backend.utils.misc import html_cleanup, html_cleanup_with_structure

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


def get_node_quantifier(node, target='*', indent=1):
    children = node.xpath('./%s' % (target))
    if len(children) > 0:
        result = []
        result_len = 0
        result_content = u''
        for c in children:
            result += get_node_quantifier(c, target, indent + 1)
        result_len = sum([x[3] for x in result if x[0] == indent + 1])
        result += [(indent, target, result_content, result_len, node.tag, node)]
        return result
    else:  # sentinel
        content = re.sub('\s+', u' ', u' '.join(node.xpath('.//text()')))
        return [(indent, target, content, len(content), node.tag, node)]


def print_node_quantifier_result(results):
    for indent, target, content, con_len, node_tag, node in results:
        if node_tag not in ('script', 'style') and con_len > 100 and content.strip() != u'':
            print >>sys.stderr, "%s%s (%s): %s" % ("*"*indent, target, con_len, content)


def get_node_quantifier_as_html(results):
    result = u''
    for indent, target, content, con_len, node_tag, node in results:
        if node_tag not in ('script', 'style') and con_len > 100 and content.strip() != u'':
            result += etree.tostring(node)
    return result


class FeedPhantomJSItem(FeedItem, HttpRequestMixin):
    def safe_xpath_string(self, strvar):
        if "'" in strvar:
            return "',\"'\",'".join(strvar.split("'")).join(("concat('","')"))
        return strvar.join("''")

    def get_combined_index_data(self):
        combined_index_data = super(
            FeedPhantomJSItem, self).get_combined_index_data()

        r = self.http_session.get(self.original_item['link'])
        print >>sys.stderr, "Got %s with status code : %s" % (
            self.original_item['link'], r.status_code)

        # only continue if we got the page
        if r.status_code < 200 or r.status_code >= 300:
            return combined_index_data

        try:
            full_content = r.content
        except etree.ElementTree.ParseError as e:
            return combined_index_data

        clean_content = html_cleanup_with_structure(full_content)
        html = etree.HTML(clean_content)

        clean_desc = html_cleanup_with_structure(
            combined_index_data['description']).replace('&nbsp;', '').strip()
        # print >>sys.stderr, "Parsing went ok..., now searching for %s" % (
        #     clean_desc[0:20])

        try:
            body = html.xpath('./body')[0]
        except Exception as e:
            body = None

        if body is None:
            return combined_index_data

        result = get_node_quantifier(body)
        combined_index_data['description'] = get_node_quantifier_as_html(result)
        print_node_quantifier_result(result)
        # print >>sys.stderr, "Found %s divs (%s)" % (len(divs), ','.join([x.tag for x in divs]))
        #
        # lengths = []
        # for div in divs:
        #     l = u' '.join(div.xpath('.//text()'))
        #     lengths.append(len(re.sub('\s+', ' ', l)))
        # print >>sys.stderr, "Lengths: %s" % (u','.join([str(l) for l in lengths]))
        # # might need to extract xpath here for better results
        # try:
        #     e = html.xpath(
        #         '//body//*[starts-with(text(),%s)]' % (
        #             self.safe_xpath_string(
        #                 clean_desc[0:20]),))[0]
        # except LookupError as e:
        #     print >>sys.stderr, e
        #     e = None
        output = u''
        # if e is not None:
        #     p = e  # .getparent()
        #     while p is not None and p.tag not in ['div', 'article', 'section']:
        #         p = p.getparent()
        #
        #     if p is not None:
        #         output = etree.tostring(p.getparent())

        if output.strip() != u'':
            # print >>sys.stderr, output
            combined_index_data['description'] = unicode(output)

        return combined_index_data
