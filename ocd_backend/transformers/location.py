from redis import StrictRedis
from ocd_backend.transformers import NoneTransformer


class LocationTransformer(NoneTransformer):
    def transform_item(self, raw_item_content_type, raw_item, item):
        # the lookup table should be (temporarily?) stored into redis)
        if 'location' in item:
            redis = StrictRedis(host='redis')
            lookup = redis.hmget('pfl_locs_norm', item['location'])
            if lookup[0] is not None:
                item['location'] = lookup

        return (
            item['meta']['_id'],
            item['meta']['_id'],
            item,
            item
        )
