import feedparser
import json
import time

from ocd_backend.extractors.staticfile import StaticFileBaseExtractor


class FeedDateEncoder(json.JSONEncoder):
    """
    Encodes the date/time structs used in the feedparser.
    """
    def default(self, obj):
        if isinstance(obj, time.struct_time):
            return time.strftime("%Y-%m-%dT%H:%M:%S%z", obj)
        return json.JSONEncoder.default(self, obj)


class FeedExtractor(StaticFileBaseExtractor):
    """
    Extract items from an RSS/Atom Feed
    """
    def extract_items(self, static_content):
        self.feedparser = feedparser.parse(static_content)
        for entry in self.feedparser.entries:
            yield 'application/json', json.dumps(entry, cls=FeedDateEncoder)
