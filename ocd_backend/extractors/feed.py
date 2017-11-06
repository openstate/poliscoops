import feedparser
import json
import time

from ocd_backend.extractors import BaseExtractor
from ocd_backend.exceptions import ConfigurationError


class FeedDateEncoder(json.JSONEncoder):
    """
    Encodes the date/time structs used in the feedparser.
    """
    def default(self, obj):
        if isinstance(obj, time.struct_time):
            return time.strftime("%Y-%m-%dT%H:%M:%S%z", obj)
        return json.JSONEncoder.default(self, obj)


class FeedExtractor(BaseExtractor):
    """
    Extract items from an RSS/Atom Feed
    """
    def __init__(self, *args, **kwargs):
        super(FeedExtractor, self).__init__(*args, **kwargs)

        if 'file_url' not in self.source_definition:
            raise ConfigurationError('Missing \'file_url\' definition')

        if not self.source_definition['file_url']:
            raise ConfigurationError('The \'file_url\' is empty')

        self.file_url = self.source_definition['file_url']

    def run(self):
        self.feedparser = feedparser.parse(self.file_url)
        for entry in feedparser.entries:
            yield 'application/json', json.dumps(entry, cls=FeedDateEncoder)
