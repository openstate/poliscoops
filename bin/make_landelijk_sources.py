#!/usr/bin/env python

import os
import sys
import json
import csv

sys.path.insert(0, '.')
from ocd_backend.utils.misc import slugify


def get_facebook_path(full_url):
    parts = full_url.replace(
        "https://www.facebook.com/", "").split("/")
    first_part = parts[0]
    if first_part in ['groups', 'pages']:
        return "%s/%s" % (parts[0], parts[1],)
    else:
        return first_part


def convert_party(party):
    slug = slugify(party['partij']).replace('-', '_')
    slug_location = 'nederland'

    # feed_type_defs = {
    #     'Feed': {
    #         "extractor": "ocd_backend.extractors.feed.FeedExtractor",
    #         "item": "ocd_backend.items.feed.FeedContentFromPageItem",
    #         'env': {
    #
    #         }
    #     },
    #     'Facebook': {
    #         "extractor": "ocd_backend.extractors.facebook.FacebookExtractor",
    #         "item": "ocd_backend.items.facebook.PageItem",
    #         'env': {
    #             'app_secret': os.environ.get('FACEBOOK_APP_SECRET', None),
    #             'app_id': os.environ.get('FACEBOOK_APP_ID', None),
    #             "paging": False,
    #             "api_version": "v2.11",
    #             "graph_url": "%s/posts" % (
    #                 get_facebook_path(party[feed_type]),)
    #         }
    #     }
    # }

    feed_id = "%s_%s_1" % (slug, slug_location,)

    result = {
        "extractor": "",  # depends if feed or not
        "keep_index_on_update": True,
        "enrichers": [
          # [
          #   "ocd_backend.enrichers.NEREnricher",
          #   {}
          # ],
          # [
          #   "ocd_backend.enrichers.BinoasEnricher",
          #   {}
          # ]
        ],
        "file_url": party['website'],
        "index_name": slug,
        "transformer": "ocd_backend.transformers.BaseTransformer",
        "collection": party['partij'],
        "loader": "ocd_backend.loaders.ElasticsearchLoader",
        "item": "",  # html grabber
        "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
        "location": 'Nederland',
        "hidden": False,
        "id": feed_id
    }

    if party['feed'] != '':
        result['extractor'] = "ocd_backend.extractors.feed.FeedExtractor"
        result['item'] = "ocd_backend.items.feed.FeedContentFromPageItem"
    else:
        result['extractor'] = "ocd_backend.extractors.staticfile.StaticHtmlExtractor"
        result['item_xpath'] = ''
    return result


def _get_normalized_locations():
    loc_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        '/opt/pfl/ocd_backend/data/cbs-name2018-mapping.csv')
    result = {}
    with open(loc_path) as locations_in:
        locations = reader = csv.reader(locations_in)
        headers = locations.next()
        for location in locations:
            record = dict(zip(headers, location))
            result[record[u'Key_poliflw']] = record[u'Alt_map']
    return result


def _normalize_location(location, LOCATIONS):
    if unicode(location) in LOCATIONS:
        return LOCATIONS[unicode(location)]
    return unicode(location)


def main(argv):
    parties = []

    result = []
    with open('/opt/pfl/ocd_backend/data/landelijk.json') as in_file:
        parties = json.load(in_file)

    for party in parties:
        result.append(convert_party(party))

    print json.dumps(result, indent=2)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
