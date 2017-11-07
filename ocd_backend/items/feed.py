from datetime import datetime

import iso8601

from ocd_backend.items import BaseItem


class FeedItem(BaseItem):
    def get_original_object_id(self):
        return unicode(self.original_item['id'])

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
            'hidden': self.source_definition['hidden']
        }

        # TODO: provide easier way for default mapping
        mappings = {
            'updated': 'date',  # default mapping
            'summary': 'description'
        }
        mappings.update(self.source_definition.get('mappings', {}))

        for fld in ['title', 'summary', 'updated']:
            if self.original_item.get(fld, None) is not None:
                mapping_fld = mappings.get(fld, fld)
                combined_index_data[mapping_fld] = self.original_item[fld]

        combined_index_data['date_granularity'] = 12

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
