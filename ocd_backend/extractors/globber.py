from glob import glob
import json

from ocd_backend.extractors import BaseExtractor
from ocd_backend.exceptions import ConfigurationError


class GlobExtractor(BaseExtractor):
    def __init__(self, *args, **kwargs):
        super(GlobExtractor, self).__init__(*args, **kwargs)

        if 'pathname' not in self.source_definition:
            raise ConfigurationError('Missing \'pathname\' definition')

        self.pathname = self.source_definition['pathname']

    def run(self):
        for file_path in glob(self.pathname):
            yield 'application/json', json.dumps({'file': file_path})
