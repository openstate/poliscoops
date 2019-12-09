from copy import deepcopy
import sys
from ocd_backend import settings
from ocd_backend.es import elasticsearch
from ocd_backend.log import get_source_logger

from elasticsearch.helpers import bulk

# weird shit that resolves some utf-8 processing with ES bulk helpers
# See https://stackoverflow.com/a/17628350
reload(sys)
sys.setdefaultencoding('utf-8')

log = get_source_logger('as2')

class AS2ConverterMixin(object):
    def as2_transform_old_object(self, actual_combined_index_data):
        combined_index_data = {
            'hidden': actual_combined_index_data.get('hidden', False),
            'meta': actual_combined_index_data.get('meta', {})
            # 'source': unicode(
            #     self.source_definition.get('source', 'Partij nieuws')),
            # 'type': unicode(self.source_definition.get('type', 'Partij')),
            # 'parties': [unicode(self.source_definition['collection'])]
        }
        loc = actual_combined_index_data.get('location', u'NL')
        party_name = unicode(actual_combined_index_data['parties'][0])
        parties = [self.get_organization(p, loc) for p in actual_combined_index_data.get('parties', [])]
        persons = [self.get_person(p, loc) for p in actual_combined_index_data.get('politicians', [])]
        content = actual_combined_index_data.get('description', None)
        pub_date = actual_combined_index_data.get('date', None)
        actual_link = actual_combined_index_data.get('link', None) or actual_combined_index_data['meta']['original_object_urls']['html']
        all_items = []
        note = {
            "@type": "Note",
            "name": unicode(actual_combined_index_data.get('title', None)),
            "content": unicode(content),
            "created": pub_date,
            "@id": self.get_identifier('Note', actual_link),
            "tag": [p['@id'] for p in parties] + [p['@id'] for p in persons],
            "url": actual_link
        }
        note_creation = {
            "@type": "Create",
            "created": pub_date,
            "actor": self.get_organization(
                party_name, loc)['@id'],
            "object": note['@id'],
            #            "@context": "http://www.w3.org/ns/activitystreams"
        }
        all_items += parties
        all_items += persons
        all_items += [note, note_creation]
        combined_index_data['item'] = {
            "@type": "OrderedCollection",
            "items": all_items
        }
        return combined_index_data

    def as2_index(self, combined_index_doc, items):
        items_to_index = []
        for d in items:
            log.info('Indexing AS2 document : ' + d['@type'])
            log.info(d)
            try:
                d_id = d['@id'].split('/')[-1]
            except LookupError:
                d_id = None
            # TODO: deal with ids in the meta object, but copy it over from the
            # parent for now... (does not seeem to affect anything though)
            items_to_index.append({
                '_index': settings.COMBINED_INDEX,
                '_type': d['@type'],
                '_id': d_id,
                'hidden': combined_index_doc['hidden'],
                'item': d,
                'meta': combined_index_doc['meta']
            })
        bulk(elasticsearch, items_to_index)
