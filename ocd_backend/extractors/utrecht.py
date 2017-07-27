from ocd_backend.extractors import BaseExtractor, HttpRequestMixin
from ocd_backend.exceptions import ConfigurationError

from click import progressbar
from datetime import datetime
import gzip
import json
from lxml import etree


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
