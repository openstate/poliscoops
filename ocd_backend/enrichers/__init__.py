# -*- coding: utf-8 -*-

from ocd_backend import celery_app
from ocd_backend import settings
from ocd_backend.exceptions import SkipEnrichment
from ocd_backend.log import get_source_logger
from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.utils import json_encoder
from ocd_backend.utils.azure import AzureTranslationMixin
from ocd_backend.utils.misc import html_cleanup

from ocd_ml.interestingness import featurize, class_labels

import datetime
import json
import pytz
import iso8601
import pickle
import os
import sys

log = get_source_logger('enricher')

interestingness_path = '/opt/pfl/interestingness.model'
if os.path.exists(interestingness_path):
    clf = pickle.load(open(interestingness_path, 'rb'))
else:
    clf = None


class BaseEnricher(celery_app.Task):
    """The base class that enrichers should inherit."""

    def run(self, *args, **kwargs):
        """Start enrichment of a single item.

        This method is called by the transformer or by another enricher
        and expects args to contain a transformed (and possibly enriched)
        item. Kwargs should contain the ``source_definition`` dict.

        :param item: The item tuple as returned by a transformer or by
            a previously runned enricher.
        :param source_definition: The configuration of a single source in
            the form of a dictionary (as defined in the settings).
        :type source_definition: dict.
        :param enricher_settings: The settings for the requested enricher,
            as provided in the source definition.
        :type enricher_settings: dict.
        :returns: the output of :py:meth:`~BaseEnricher.enrich_item`
        """

        self.source_definition = kwargs['source_definition']
        self.enricher_settings = kwargs['enricher_settings']

        combined_object_id, object_id, combined_index_doc, doc = args[0]
        try:
            enrichments = self.enrich_item(
                doc['enrichments'],
                object_id,
                combined_index_doc,
                doc
            )
        except SkipEnrichment as e:
            log.info('Skipping %s for %s, reason: %s'
                     % (self.__class__.__name__, object_id, e.message))
            return (combined_object_id, object_id, combined_index_doc, doc)
        except:
            log.exception('Unexpected error, skipping %s for %s'
                          % (self.__class__.__name__, object_id))
            return (combined_object_id, object_id, combined_index_doc, doc)

        # Add the modified 'enrichments' dict to the item documents
        # note updates the entire document for Poliflw
        # log.exception('Indexing updating with: %s' % (enrichments,))

        combined_index_doc.update(enrichments)
        doc.update(enrichments)

        # log.exception('Indexing combined is now: %s' % (combined_index_doc,))
        return (combined_object_id, object_id, combined_index_doc, doc)

    def enrich_item(self, enrichments, object_id, combined_index_doc, doc):
        """Enriches a single item.

        This method should be implemented by the class that inherits
        from :class:`.BaseEnricher`. The method should modify and return
        the passed ``enrichments`` dictionary. The contents of the
        ``combined_index_doc`` and ``doc`` can be used to generate the
        enrichments.

        :param enrichments: the dict that should be modified by the
            enrichment task. It is possible that this dictionary already
            contains enrichments from previous tasks.
        :type enrichments: dict
        :param object_id: the identifier of the item that is being enriched.
        :type object_id: str
        :param combined_index_doc: the 'combined index' representation
            of the item.
        :type combined_index_doc: dict
        :param doc: the collection specific index representation of the
            item.
        :type doc: dict
        :returns: a modified enrichments dictionary.
        """
        raise NotImplemented


class PoliTagsEnricher(BaseEnricher, HttpRequestMixin):
    def _perform_ner(self, doc_id, doc):
        # FIXME: sometimes we use short names for parties and sometimes not
        parties2names = {
            u'Christen-Democratisch Appèl': u'CDA',
            u'Democraten 66': u'D66',
            u'Partij van de Arbeid': u'PvdA',
            u'Staatkundig Gereformeerde Partij': u'SGP',
            u'Socialistische Partij': u'SP',
            u'Volkspartij voor Vrijheid en Democratie': u'VVD'
        }

        url = 'http://politags_web_1:5000/api/articles/entities'
        politicians = doc.get('politicians', [])
        parties = doc.get('parties', [])
        topics = doc.get('topics', [])
        sentiment = doc.get('sentiment', {})

        doc['id'] = unicode(doc_id)
        doc['meta']['pfl_url'] = unicode("https://api.poliflw.nl/v0/%s/%s" % (
            doc['meta']['source_id'], doc_id,))
        try:
            resp = self.http_session.post(
                url, data=json_encoder.encode(doc),
                headers={'Content-type': 'application/json'})
            r = resp.json()
        except Exception as e:
            log.exception('Unexpected NER enrichment error: %s'
                          % (e.message,))
            # log.exception(resp.content)
            # log.exception(json_encoder.encode(doc))

            r = {
                'parties': [], 'politicians': [], 'topics': [], 'sentiment': {}
            }

        log.exception('NER response:')
        log.exception(r)
        log.exception('Indexing found topics: %s' % (r.get('topics', []),))
        log.exception('Indexing found sentiment: %s' % (r.get('sentiment', {}),))
        return {
            'topics': r.get('topics', []),
            'sentiment': r.get('sentiment', {}),
            'parties': parties + [parties2names.get(p['name'], p['name']) for p in r['parties'] if p['name'] not in parties],
            'politicians': politicians + [
                u'%s %s' % (p['initials'], p['last_name'],) for p in r['politicians'] if u'%s %s' % (p['initials'], p['last_name'],) not in politicians]
        }

    def enrich_item(self, enrichments, object_id, combined_index_doc, doc):
        enrichments.update(self._perform_ner(object_id, combined_index_doc))
        return enrichments


# class InterestingnessEnricher(BaseEnricher, HttpRequestMixin):
class InterestingnessEnricher(PoliTagsEnricher):
    def _perform_interestingness(self, object_id, combined_index_doc):
        res = clf.predict([featurize(combined_index_doc)])
        return {
            'interestingness': class_labels[res[0]]
        }

    def enrich_item(self, enrichments, object_id, combined_index_doc, doc):
        enrichments = super(InterestingnessEnricher, self).enrich_item(
            enrichments, object_id, combined_index_doc, doc)

        enrichments.update(self._perform_interestingness(
            object_id, combined_index_doc))

        return enrichments


# NEREnricher is merely an alias for another class, in order to avoid having
# to edit all source files.
class NEREnricher(InterestingnessEnricher):
    pass


class AS2TranslationEnricher(BaseEnricher, AzureTranslationMixin):
    def enrich_item(self, enrichments, object_id, combined_index_doc, doc):
        print >>sys.stderr, "Combined index doc has %s items" % (
            len(combined_index_doc.get('item', {}).get('items', [])),)
        enrichments['translations'] = {}
        for item in combined_index_doc.get('item', {}).get('items', []):
            # TODO: Maybe determine the type of object, if translation is needed
            # TODO: check if item exists to prevent unecesary retranslation of text we already have
            # print >>sys.stderr, item
            docs_for_translation = []
            if item.get('nameMap', {}).get('nl', None) is not None:
                docs_for_translation.append(item['nameMap']['nl'])
            # print >>sys.stderr, "Combined doc before translation: %s" % (combined_index_doc,)
            if item.get('contentMap', {}).get('nl', None) is not None:
                docs_for_translation.append(html_cleanup(item['contentMap']['nl']))
            if len(docs_for_translation) > 0:
                translations = self.translate(
                    docs_for_translation, to_lang=['en', 'de', 'fr'])
                enrichments['translations'][item['@id']] = translations
                #print >>sys.stderr, "Enrichments: %s" % (enrichments,)
        return enrichments


class BinoasEnricher(BaseEnricher, HttpRequestMixin):
    def enrich_item(self, enrichments, object_id, combined_index_doc, doc):
        doc['id'] = unicode(object_id)
        if 'meta' in doc:
            doc['meta']['pfl_url'] = unicode(
                "https://api.poliflw.nl/v0/%s/%s" % (
                    doc['meta']['source_id'], object_id,))

        if 'date' not in doc:
            log.info(
                'Document has no date information, not enriching for binoas')
            return enrichments

        amsterdam_tz = pytz.timezone('Europe/Amsterdam')
        current_dt = datetime.datetime.now(tz=amsterdam_tz)
        try:
            current_tz = doc['date'].tzinfo
        except AttributeError:
            current_tz = None
        if current_tz is not None:
            delay = current_dt - doc['date']
        else:
            # adjust for amsterdam time
            adjusted_dt = iso8601.parse_date('%s+02:00' % (
                doc['date'].isoformat()))
            delay = current_dt - adjusted_dt

        if delay.total_seconds() > (6 * 3600.0):
            log.info('Document delayed for %s so we have seen it before' % (
                str(delay),))
            return enrichments

        url = 'http://binoas.openstate.eu/posts/new'
        r = {}
        resp = None
        log.info('sending to binoas: ' + str(doc))
        try:
            resp = self.http_session.post(
                url, data=json_encoder.encode({
                    'application': 'poliflw',
                    'payload': doc}))
            r = resp.json()
        except Exception as e:
            log.exception('Unexpected binoas enrichment error: %s'
                          % (e.message,))
            log.exception(resp.content)
            log.exception(doc)
        log.info('binoas result: ' + str(r))
        return enrichments
