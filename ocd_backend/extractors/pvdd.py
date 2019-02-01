from ocd_backend.extractors import BaseExtractor, HttpRequestMixin

from lxml import etree

import re
from urlparse import urljoin


class PVDDExtractor(BaseExtractor, HttpRequestMixin):
    def get_collection_objects(self):
        url = self.source_definition['file_url']
        paging = self.source_definition.get('paging', False)

        all_links_xpath = ".//article/header/h2|.//div[contains(@class, \"article\")]/div"

        # Continue loop until a page contains no items
        page = 1
        finished = False
        while not finished:
            resp = self.http_session.get('%s/?page=%s' % (url, str(page)))

            # check if we get good status codes
            if (resp.status_code >= 300) or (resp.status_code < 200):
                print "Page %s (%s) got status code: %s" % (resp.url, resp.status_code,)

                if paging:
                    page += 1  # we can continue?
                else:
                    finished = True
                continue

            html = etree.HTML(resp.content)

            # Loop over all div's containg links to item pages
            items = html.xpath(all_links_xpath)
            # If there are no items then stop
            if not items:
                finished = True

            for item in items:
                link = item.xpath("a/@href")
                if link:
                    link = urljoin(url, link[0])
                    yield link

            if not paging:
                finished = True

            page += 1

    def get_object(self, item_url):
        resp = self.http_session.get(item_url)
        return 'application/html', resp.content

    def run(self):
        for item_url in self.get_collection_objects():
            yield self.get_object(item_url)
