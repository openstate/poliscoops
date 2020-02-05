from copy import deepcopy
import datetime
import sys
from urlparse import urljoin

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
        language = actual_combined_index_data.get('language', 'nl')
        loc = actual_combined_index_data.get('location', u'NL')
        location = {
            "@id": self.get_identifier('Place', loc),
            "@type": "Place",
            "nameMap": {
                language: loc
            }
        }
        generator_name = actual_combined_index_data.get('source', 'PoliScoops')
        generator_url = "https://poliscoops.com/#%s" % (generator_name,)
        generator = {
            "@id": self.get_identifier('Link', generator_url),
            "@type": "Link",
            "href": generator_url,
            "name": generator_name,
            "rel": "canonical"
        }
        party_name = unicode(actual_combined_index_data['parties'][0])
        parties = [self.get_organization(p, loc) for p in actual_combined_index_data.get('parties', [])]
        persons = [self.get_person(p, loc) for p in actual_combined_index_data.get('politicians', [])]
        topics = [self.get_topic(t.get('name', '-'), loc) for t in actual_combined_index_data.get('topics', [])]
        sentiments = self.get_sentiment(actual_combined_index_data.get('sentiment', {}))
        content = actual_combined_index_data.get('description', None)
        pub_date = actual_combined_index_data.get('date', None)
        actual_link = actual_combined_index_data.get('link', None) or actual_combined_index_data['meta']['original_object_urls']['html']
        interestingness = self.get_interestingness(actual_combined_index_data.get('interestingness', 'laag'))
        news_type = self.get_type(actual_combined_index_data.get('type', 'Partij'))
        all_items = [interestingness, news_type, location, generator]
        note_actor = self.get_organization(
            party_name, loc)['@id']
        note = {
            "@type": "Note",
            "nameMap": {
                language: unicode(actual_combined_index_data.get('title', None))
            },
            "contentMap": {
                language: unicode(content)
            },
            "created": pub_date,
            "@id": self.get_identifier('Note', actual_link),
            "location": location['@id'],
            "generator": generator['@id'],
            "tag": [p['@id'] for p in parties] + [p['@id'] for p in persons] + [s['@id'] for s in sentiments] + [interestingness['@id'], news_type['@id']],
            "origin": [t['@id'] for t in topics],
            "url": actual_link,
            "attributedTo": note_actor
        }
        note_creation = {
            "@type": "Create",
            "created": pub_date,
            "actor": note_actor,
            "object": note['@id'],
            #            "@context": "http://www.w3.org/ns/activitystreams"
        }
        all_items += parties
        all_items += persons
        all_items += topics
        all_items += sentiments
        all_items += [note, note_creation]
        combined_index_data['item'] = {
            "@type": "OrderedCollection",
            "items": all_items
        }
        return combined_index_data

    def as2_index(self, combined_index_doc, items):
        items_to_index = []
        for d in items:
            try:
                d_id = d['@id'].split('/')[-1]
            except LookupError:
                d_id = None
            #print >>sys.stderr, combined_index_doc['translations']
            translations = combined_index_doc.get('translations', {}).get(d.get('@id', ''), [])
            if len(translations) == 0:
                translation_keys = {}
            if len(translations) == 1:
                translation_keys = {0: 'contentMap'}
            if len(translations) == 2:
                translation_keys = {0: 'nameMap', 1: 'contentMap'}
            for t_idx, t_key in translation_keys.iteritems():
                d[t_key] = {x['to']: x['text'] for x in translations[t_idx]['translations']}

                # always take the language of the content, since content tends to
                # be longer than the title
                d['@language'] = translations[-1]['detectedLanguage']['language']

            items_to_index.append({
                '_index': settings.COMBINED_INDEX,
                '_type': d['@type'],
                '_id': d_id,
                'hidden': combined_index_doc.get('hidden', False),
                'item': d,
                #'enrichments': {'translations': translations},
                'meta': {
                    'processing_started': datetime.datetime.now(),
                    'processing_finished': datetime.datetime.now(),
                    'source_id': 'whatever',
                    'collection': 'whatever',
                    'rights': u'unknown',
                    'original_object_id': d_id,
                    'original_object_urls': {
                        'html': urljoin(
                            urljoin(settings.AS2_NAMESPACE, d['@type']), d_id)
                    },
                }
            })
        bulk(elasticsearch, items_to_index)
