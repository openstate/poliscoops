import json
from pprint import pprint
import re

from ocd_backend.extractors import BaseExtractor, HttpRequestMixin
from ocd_backend.exceptions import ConfigurationError
from ocd_backend.utils.api import FrontendAPIMixin

from ocd_backend import settings


class FrontendAPIExtractor(BaseExtractor, HttpRequestMixin, FrontendAPIMixin):
    """
    Extracts items from the frontend API.
    """
    def run(self):
        n_from = self.source_definition.get('frontend_args', {}).get('from', 0)
        n_size = self.source_definition.get(
            'frontend_args', {}).get('size', 10)
        n_results = n_size
        params = self.source_definition['frontend_args']
        while (n_results == n_size):
            print "Getting %s results from %s " % (n_size, n_from,)
            results = self.api_request(
                self.source_definition['index_name'],
                self.source_definition['frontend_type'], **params)
            n_from += n_results
            n_results = len(results)
            params['from'] = n_from
            for result in results:
                # print "%s - %s" % (result['id'], result['classification'],)
                # pprint(result)
                print u"%s - %s (%s)" % (
                    result.get('date', '-'), result.get('title', '-'),
                    result['meta']['_id'],)
                yield 'application/json', json.dumps(result)
            print "Got %s results" % (n_results,)
