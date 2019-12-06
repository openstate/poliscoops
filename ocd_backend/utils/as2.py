from copy import deepcopy

from ocd_backend import settings

class AS2ConverterMixin(object):
    def as2_transform_old_object(self, actual_combined_index_data):
        combined_index_data = {
            'hidden': actual_combined_index_data.get('hidden', False),
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
            "name": actual_combined_index_data.get('title', None),
            "content": content,
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
