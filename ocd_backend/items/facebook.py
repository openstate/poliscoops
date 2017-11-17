from datetime import datetime

import iso8601

from ocd_backend.items import BaseItem


class PageItem(BaseItem):
    def get_original_object_id(self):
        return unicode(self.original_item['id'])

    def get_original_object_urls(self):
        return {
            'html': u'https://www.facebook.com/%s/posts/%s' % (
                self.source_definition['facebook']['graph_url'].split('/')[0],
                self.original_item['id'].split('_')[1],)
        }

    def get_rights(self):
        return unicode(self.original_item.get('rights', 'Undefined'))

    def get_collection(self):
        return unicode(self.source_definition.get('collection', 'Unknown'))

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden'],
            'source': unicode(
                self.source_definition.get('source', 'Facebook')),
            'type': unicode(self.source_definition.get('type', 'Partij')),
            'parties': [unicode(self.source_definition['collection'])]
        }

        combined_index_data['description'] = unicode(
            self.original_item['message'])

        try:
            combined_index_data['date'] = iso8601.parse_date(
                self.original_item['created_time'])
        except LookupError:
            pass

        if self.source_definition.get('location', None) is not None:
            combined_index_data['location'] = unicode(self.source_definition[
                'location'])
        combined_index_data['date_granularity'] = 12

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
