# -*- coding: utf-8 -*-

# This simple app uses the '/translate' resource to translate text from
# one language to another.

# This sample runs on Python 2.7.x and Python 3.x.
# You may need to install requests and uuid.
# Run: pip install requests uuid

import sys, os, requests, uuid, json, codecs, urllib

from ocd_backend.settings import AZURE_TEXT_TRANSLATOR_KEY, AZURE_TEXT_MAX_LENGTH

class BaseAzureMixin(object):
    pass

class AzureTranslationMixin(BaseAzureMixin):
    def translate(self, text, from_lang=None, to_lang=None):
        endpoint = 'https://api.cognitive.microsofttranslator.com'
        subscription_key = AZURE_TEXT_TRANSLATOR_KEY
        path = '/translate'
        params = {
            'api-version': '3.0'
        }
        if from_lang is not None:
            params['from'] = from_lang
        if to_lang is not None:
            params['to'] = to_lang
        constructed_url = endpoint + path + '?' + urllib.urlencode(params, True)
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        body = []
        if isinstance(text, list):
            tl = AZURE_TEXT_MAX_LENGTH - 250  # shorter because of title
            body = [{'text': t[:tl]} for t in text]
        else:
            body = [{'text': text[:AZURE_TEXT_MAX_LENGTH]}]
        request = requests.post(constructed_url, headers=headers, data=json.dumps(body))
        response = request.json()
        print >>sys.stderr, "r: %s" % (response,)
        for b, d in zip(body, response):
            #print >>sys.stderr, "b: %s" % (b,)
            #print >>sys.stderr, "d: %s" % (d,)
            d[u'translations'].append({u'text': b[u'text'], u'to': d[u'detectedLanguage'][u'language']})
        return response
