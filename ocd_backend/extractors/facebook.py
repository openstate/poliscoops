from ocd_backend.extractors import BaseExtractor, HttpRequestMixin
from ocd_backend.exceptions import ConfigurationError

import json


class FacebookExtractor(BaseExtractor, HttpRequestMixin):
    "A class that extracts stuff from Facebook, Using the Graph API."
    def __init__(self, *args, **kwargs):
        super(FacebookExtractor, self).__init__(*args, **kwargs)

        if 'facebook' not in self.source_definition:
            raise ConfigurationError('Missing \'facebook\' definition')

        for fld in [
            'api_version', 'app_id', 'app_secret', 'graph_url'
        ]:
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

    def _fb_get_object(self, next_url=None):
        if next_url is not None:
            graph_url = next_url
        else:
            # TODO: needs to point to posts, but have feecd in the sources config. Now for a quick fix
            graph_url = "https://graph.facebook.com/%s/%s?fields=id,name,message,link,picture,description,created_time&access_token=%s" % (
                self.fb_api_version, self.fb_graph_url.replace('/feed', '/posts'),
                self._fb_get_access_token(),)
        r = self.http_session.get(graph_url)
        # check if we get good status codes
        if (r.status_code >= 300) or (r.status_code < 200):
            print "%s got status code: %s" % (graph_url, r.status_code,)
            print r.content
            return {'data': []}  # return an empty object
        return r.json()

    def run(self):
        do_paging = self.source_definition['facebook'].get('paging', False)
        obj = self._fb_get_object()
        for item in obj['data']:
            yield 'application/json', json.dumps(item)
        while do_paging and ('paging' in obj) and ('next' in obj['paging']):
            obj = self._fb_get_object(obj['paging']['next'])
            for item in obj['data']:
                yield 'application/json', json.dumps(item)
