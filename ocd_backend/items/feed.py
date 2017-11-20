from datetime import datetime

import iso8601

from ocd_backend.items import BaseItem


class FeedItem(BaseItem):
    def get_original_object_id(self):
        return unicode(self.original_item['link'])

    def get_original_object_urls(self):
        return {
            'html': self.original_item['link']
        }

    def get_rights(self):
        return unicode(self.original_item.get('rights', 'Undefined'))

    def get_collection(self):
        return unicode(self.source_definition.get('collection', 'Unknown'))

    def get_combined_index_data(self):
        combined_index_data = {
            'hidden': self.source_definition['hidden'],
            'source': unicode(
                self.source_definition.get('source', 'Partij nieuws')),
            'type': unicode(self.source_definition.get('type', 'Partij')),
            'parties': [unicode(self.source_definition['collection'])]
        }

        # TODO: provide easier way for default mapping
        mappings = {
            'summary': 'description'
        }
        mappings.update(self.source_definition.get('mappings', {}))

        for fld in ['title', 'summary']:
            if self.original_item.get(fld, None) is not None:
                mapping_fld = mappings.get(fld, fld)
                combined_index_data[mapping_fld] = self.original_item[fld]

        # try to get the full content, if available
        try:
            combined_index_data['description'] = self.original_item[
                'content'][0]['value']
        except LookupError:
                pass

        try:
            combined_index_data['date'] = iso8601.parse_date(
                self.original_item['published_parsed'])
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
