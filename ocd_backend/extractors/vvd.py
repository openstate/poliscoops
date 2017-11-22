import datetime
import urlparse

from lxml import etree

from ocd_backend.extractors.paging import PagedStaticHtmlExtractor


class VVDHtmlExtractor(PagedStaticHtmlExtractor):
    def _get_next_page(self, static_content):
        self.year = self.year - 1
        html = etree.HTML(static_content)
        min_year = min(
            [int(x) for x in html.xpath(
                '//div[@class=\"aside__container\"]//nav/ul/li/a/span/text()')]
        )

        if self.year < min_year:
            return None

        return urlparse.urljoin(
            self.file_url, '/nieuws/archief/%s' % (self.year,))

    def run(self):
        self.year = datetime.datetime.now().year
        self.file_url = urlparse.urljoin(
            self.file_url, '/nieuws/archief/%s' % (self.year,))
        return super(VVDHtmlExtractor, self).run()
