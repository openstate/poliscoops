#!/usr/bin/env python

import sys
import json

sys.path.insert(0, '.')
from ocd_backend.utils.misc import slugify


def convert_party(party):
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
        "location": party['RegioNaam'],
        "hidden": False,
        "id": "%s_%s_1" % (slug, slug_location,)
    }

    return result


def main(argv):
    parties = []

    result = []
    with open('/opt/pfl/ocd_backend/data/lokaal.json') as in_file:
        parties = json.load(in_file)

    for party in parties:
        if party['Feed'] != '':
            result.append(convert_party(party))

    print json.dumps(result, indent=2)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
