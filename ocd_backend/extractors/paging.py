from lxml import etree
import urlparse
import json

from ocd_backend.extractors.staticfile import StaticHtmlExtractor
from ocd_backend.exceptions import ConfigurationError


class PagedStaticHtmlExtractor(StaticHtmlExtractor):
    def __init__(self, *args, **kwargs):
        super(PagedStaticHtmlExtractor, self).__init__(*args, **kwargs)
        self.paging_xpath = self.source_definition.get('paging_xpath', None)

    def _get_next_page(self, static_content):
        if self.paging_xpath is not None:
            result = self.tree.xpath(self.paging_xpath)
            if result:
                return urlparse.urljoin(
                    self.source_definition['file_url'], result[0])
        return None

    def extract_items(self, static_content):
        self.tree = etree.HTML(static_content)

        self.namespaces = None
        if self.default_namespace is not None:
            # the namespace map has a key None if there is a default namespace
            # so the configuration has to specify the default key
            # xpath queries do not allow an empty default namespace
            self.namespaces = self.tree.nsmap
            try:
                self.namespaces[self.default_namespace] = self.namespaces[None]
                del self.namespaces[None]
            except KeyError:
                pass

        for item in self.tree.xpath(
            self.item_xpath, namespaces=self.namespaces
        ):
                yield item

    def run(self):
        # Retrieve the static content from the source
        finished = False
        static_url = self.file_url
        while not finished:
            print "Fetching url : %s" % (static_url,)
            r = self.http_session.get(static_url)

            # check if we get good status codes
            if (r.status_code >= 300) or (r.status_code < 200):
                print "%s got status code: %s" % (static_url, r.status_code,)
                finished = True
                continue

            static_content = r.content

            # Extract and yield the items
            for item in self.extract_items(static_content):
                link = urlparse.urljoin(
                    self.source_definition['file_url'],
                    item.xpath(self.source_definition['item_link_xpath'])[0])
                print link
                yield 'application/json', json.dumps({'link': link})

            static_url = self._get_next_page(static_content)
            finished = (static_url is None)
