import json

from lxml import etree

from ocd_backend.extractors.staticfile import StaticFileBaseExtractor
from ocd_backend.utils.linkmap import build_linkmap, save_linkmap, load_linkmap

class LinkmapExtractor(StaticFileBaseExtractor):
    def extract_items(self, static_content):
        tree = etree.HTML(static_content)
        existing = load_linkmap(self.file_url)
        current = build_linkmap(self.file_url, tree)

        new_links = []
        if existing is not None and current is not None:
            new_links = set(existing['links'] or []) - set(current['links'] or [])

        # if not existing:
        #     save_linkmap(url, linkmap)

        for link in new_links:
            yield 'application/json', json.dumps({"link": link})
