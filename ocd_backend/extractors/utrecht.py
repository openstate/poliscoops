from ocd_backend.extractors import BaseExtractor, HttpRequestMixin
from ocd_backend.extractors.globber import GlobExtractor
from ocd_backend.exceptions import ConfigurationError

from click import progressbar
from datetime import datetime
from glob import glob
import gzip
import json
from lxml import etree
import os
from pprint import pprint
import re

from xlrd import open_workbook


class UtrechtExtractor(BaseExtractor, HttpRequestMixin):
    def get_collection_objects(self, url):
        # Retrieve start and end dates for which we want to retrieve Wob
        # info for this URL
        start = url['start']

        end = url['end']
        if end == 'today':
            end = datetime.now().isoformat()[:10]

        is_archive = False
        if url['is_archive'] == "true":
            is_archive = True
            archive_url = url['archive_url']

        website_design = 'new'
        if url['website_design'] == 'old':
            website_design = 'old'

        all_wob_links_xpath = ".//div[@class='limiter']/div"
        if website_design == 'old':
            all_wob_links_xpath = ".//div[@class='news-list-item']"

        # Continue loop until a page contains no items or the items are
        # not within the allowed date range
        page = 1
        finished = False
        while not finished:
            # TODO requests gave CERTIFICATE_VERIFY_FAILED error so
            # temporarily set verify to false; remove this and see if it
            # succeeds again later
            resp = self.http_session.get(url['url'] + '/pagina/' + str(page) + '/', verify=False)
            html = etree.HTML(resp.content)

            # Loop over all div's containg links to wob pages
            items = html.findall(all_wob_links_xpath)

            # The new design has the pagination as last div
            # so remove it
            if website_design == 'new':
                items = items[:-1]

            # If there are no items then stop
            if not items:
                finished = True

            for item in items:
                link = item.xpath("h2/a/@href")
                if link:
                    link = link[0]
                    # Skip overzicht links
                    if link.split('/')[-2].startswith('overzicht'):
                        continue

                    # Check if date is in the allowed range or
                    # stop if no date is found
                    date = item.xpath("//time/@datetime")[0][:10]
                    if date < start:
                        finished = True

                    if date > end:
                        continue

                    # Sometimes relative paths are used so prepend the
                    # domain and prepend the archive URL if an archive
                    # is crawled
                    if not link.startswith('http'):
                        link = 'https://www.utrecht.nl' + link
                        if is_archive:
                            link = archive_url + link

                    # Sometimes links contain this path, and sometimes
                    # it doesn't work; removing it does always work
                    if 'bestuur-en-organisatie/publicaties/' in link and website_design == 'old':
                        link = link.replace('bestuur-en-organisatie/publicaties/', '')
                    yield link
            page += 1

    def get_object(self, item_url):
        resp = self.http_session.get(item_url, verify=False)

        return 'application/html', resp.content

    def run(self):
        for url in self.source_definition['urls']:
            for item_url in self.get_collection_objects(url):
                yield self.get_object(item_url)


class UtrechtCateogriesExtractor(BaseExtractor, HttpRequestMixin):
    def _get_items_links_from_category(self, cat_url):
        all_wobs_xpath = "//div[@class='limiter']/div//h2/a"
        resp = self.http_session.get(cat_url, verify=False)
        html = etree.HTML(resp.content)
        # Loop over all div's containg links to wob pages
        result = {}
        for wob_obj in html.xpath(all_wobs_xpath):
            wob_url = wob_obj.xpath('.//@href')[0]
            wob_title = u''.join(wob_obj.xpath('.//text()'))
            result[wob_url] = wob_title
        return result

    def run(self):
        resp = self.http_session.get(
            self.source_definition['url'], verify=False)
        html = etree.HTML(resp.content)

        categories = {}
        titles = {}
        for cat_obj in html.xpath('//div[@class="linklijst"]/div/ul/li/a'):
            cat_url = u'https://www.utrecht.nl%s' % (
                cat_obj.xpath('.//@href')[0],)
            cat_title = u''.join(cat_obj.xpath('.//text()')).replace(
                u'Wob-verzoeken ', u'')
            item_links = self._get_items_links_from_category(cat_url)
            titles.update(item_links)
            for item_link, item_title in item_links.iteritems():
                categories.setdefault(item_link, []).append(cat_title)

        for url, categories_list in categories.iteritems():
            yield 'application/json', json.dumps({
                'url': url,
                'title': unicode(titles[url]),
                'categories': categories_list
            })


class UtrechtOverviewExtractor(GlobExtractor):
    def _get_wob_requests(self, file_path):
        wb = open_workbook(file_path)
        sh = wb.sheet_by_index(0)
        wobs = []
        header = False
        processing = False
        processed = 0
        year = int(os.path.basename(file_path)[0:4])
        for row_num in xrange(0, sh.nrows):
            values = sh.row_values(row_num)
            wob_id = values[0]
            wob_sender = values[1]
            if unicode(wob_id).strip() == u'NR.':
                header = True
                continue
            if not header:
                continue
            processing = (
                header and
                u''.join([unicode(v).strip() for v in values]) != u'')
            if header and unicode(wob_id).strip() == u'' and processed > 0:
                processing = False
                header = False
            if unicode(wob_id).strip() in [u'Totaal', u'OVERIGE']:
                processing = False
                header = False
            if unicode(wob_id).strip() == u'':
                continue
            if re.match(r'^\d{4}', unicode(wob_id).strip()):
                year = int(wob_id)
                continue
            if processing:
                print "%s-%s" % (year, values[0],)
                processed += 1
        return wobs

    def run(self):
        for file_path in glob(self.pathname):
            print file_path
            for wob in self._get_wob_requests(file_path):
                yield 'application/json', json.dumps({
                    'file': file_path, 'wob': wob})
