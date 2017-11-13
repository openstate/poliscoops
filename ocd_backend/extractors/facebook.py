from ocd_backend.extractors import BaseExtractor, HttpRequestMixin
from ocd_backend.exceptions import ConfigurationError

import json


class FacebookExtractor(BaseExtractor, HttpRequestMixin):
    "A class that extracts stuff from Facebook, Using the Graph API."
    def __init__(self, *args, **kwargs):
        super(FacebookExtractor, self).__init__(*args, **kwargs)

        if 'facebook' not in self.source_definition:
            raise ConfigurationError('Missing \'facebook\' definition')

        for fld in ['api_version', 'app_id', 'app_secret', 'graph_url']:
            if fld not in self.source_definition['facebook']:
                raise ConfigurationError(
                    'Missing \'%s\' definition of facebook' % (fld,))

            if not self.source_definition['facebook'][fld]:
                raise ConfigurationError(
                    'The \'%s\' in facebook is empty' % (fld,))

            setattr(
                self, 'fb_%s' % (fld,),
                self.source_definition['facebook'][fld])

    def _fb_get_access_token(self):
        return u"%s|%s" % (self.fb_app_id, self.fb_app_secret,)

    def _fb_get_object(self):
        graph_url = "https://graph.facebook.com/%s/%s?access_token=%s" % (
            self.fb_api_version, self.fb_graph_url,
            self._fb_get_access_token(),)
        r = self.http_session.get(graph_url, verify=False)
        r.raise_for_status()
        return r.json()

    def run(self):
        obj = self._fb_get_object()
        for item in obj['data']:
            yield 'application/json', json.dumps(item)
