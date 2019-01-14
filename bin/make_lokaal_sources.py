#!/usr/bin/env python

import os
import sys
import json
import csv

sys.path.insert(0, '.')
from ocd_backend.utils.misc import slugify


def convert_party(party, locations):
    slug = slugify(party['Partij']).replace('-', '_')
    slug_location = slugify(party['RegioNaam']).replace('-', '_')
    result = {
        "extractor": "ocd_backend.extractors.feed.FeedExtractor",
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
        "file_url": party['Feed'],
        "index_name": slug,
        "transformer": "ocd_backend.transformers.BaseTransformer",
        "collection": party['Partij'],
        "loader": "ocd_backend.loaders.ElasticsearchLoader",
        "item": "ocd_backend.items.feed.FeedPhantomJSItem",
        "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
        "location": _normalize_location(party['RegioNaam'], locations),
        "hidden": False,
        "id": "%s_%s_1" % (slug, slug_location,)
    }

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
    locations = _get_normalized_locations()
    parties = []

    result = []
    with open('/opt/pfl/ocd_backend/data/lokaal.json') as in_file:
        parties = json.load(in_file)

    for party in parties:
        if party['Feed'] != '':
            result.append(convert_party(party, locations))

    print json.dumps(result, indent=2)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
