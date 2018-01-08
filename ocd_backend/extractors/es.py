import json
from pprint import pprint

from ocd_backend import settings
from ocd_backend.extractors import BaseExtractor
from ocd_backend.exceptions import ConfigurationError
from ocd_backend.es import elasticsearch

from elasticsearch.helpers import scan


class ElasticsearchExtractor(BaseExtractor):
    def __init__(self, *args, **kwargs):
        super(ElasticsearchExtractor, self).__init__(*args, **kwargs)

    def run(self):
        es_index = self.source_definition.get(
            'elasticsearch_index', u'%s_%s' % (
                settings.DEFAULT_INDEX_PREFIX,
                self.source_definition['index_name'],))
        es_doc_type = self.source_definition.get(
            'elasticsearch_doc_type', self.source_definition['doc_type'])
        items = scan(
            elasticsearch,
            query=self.source_definition.get('elasticsearc_query', None),
            scroll=self.source_definition.get('elasticsearch_scroll', '5m'),
            raise_on_error=False, index=es_index, doc_type=es_doc_type)

        for item in items:
            for k in [u'combined_index_data', u'source_data']:
                if k in item[u'_source']:
                    del item[u'_source'][k]
            yield 'application/json', json.dumps(item[u'_source'])
