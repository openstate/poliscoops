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


def convert_party(party, feed_type, locations):
    slug = slugify(party['Partij']).replace('-', '_')
    slug_location = slugify(party['RegioNaam']).replace('-', '_')

    feed_type_defs = {
        'Feed': {
            "extractor": "ocd_backend.extractors.feed.FeedExtractor",
            "item": "ocd_backend.items.feed.FeedPhantomJSItem",
            'env': {

            }
        },
        'Facebook': {
            "extractor": "ocd_backend.extractors.facebook.FacebookExtractor",
            "item": "ocd_backend.items.facebook.PageItem",
            'env': {
                'app_secret': os.environ.get('FACEBOOK_APP_SECRET', None),
                'app_id': os.environ.get('FACEBOOK_APP_ID', None),
                "paging": False,
                "api_version": "v2.11",
                "graph_url": "%s/posts" % (
                    get_facebook_path(party[feed_type]),)
            }
        }
    }

    result = {
        "extractor": feed_type_defs[feed_type]['extractor'],
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
        feed_type.lower(): {},
        "file_url": party[feed_type],
        "index_name": slug,
        "transformer": "ocd_backend.transformers.BaseTransformer",
        "collection": party['Partij'],
        "loader": "ocd_backend.loaders.ElasticsearchLoader",
        "item": feed_type_defs[feed_type]['item'],
        "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
        "location": _normalize_location(party['RegioNaam'], locations),
        "hidden": False,
        "id": "%s_%s_1" % (slug, slug_location,)
    }

    for k, v in feed_type_defs[feed_type]['env'].iteritems():
        result[feed_type.lower()][k] = v
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
    if len(argv) > 1:
        feed_type = argv[1]
    else:
        feed_type = 'Feed'
    print >>sys.stderr, "Looking for %s sources ..." % (feed_type,)
    locations = _get_normalized_locations()
    parties = []

    result = []
    with open('/opt/pfl/ocd_backend/data/lokaal.json') as in_file:
        parties = json.load(in_file)

    for party in parties:
        if party[feed_type] != '':
            result.append(convert_party(party, feed_type, locations))

    print json.dumps(result, indent=2)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
