# -*- coding: utf-8 -*-

from ocd_backend import celery_app
from ocd_backend import settings
from ocd_backend.exceptions import SkipEnrichment
from ocd_backend.log import get_source_logger
from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.utils import json_encoder

import json

log = get_source_logger('enricher')


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
        combined_index_doc.update(enrichments)
        doc.update(enrichments)

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


class NEREnricher(BaseEnricher, HttpRequestMixin):
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
            log.exception(resp.content)
            log.exception(json_encoder.encode(doc))

            r = {'parties': [], 'politicians': []}

        log.exception('NER response:')
        log.exception(r)
        return {
            'parties': parties + [parties2names.get(p['name'], p['name']) for p in r['parties'] if p['name'] not in parties],
            'politicians': politicians + [
                u'%s %s' % (p['first_name'], p['last_name'],) for p in r['politicians'] if u'%s %s' % (p['first_name'], p['last_name'],) not in politicians]
        }

    def enrich_item(self, enrichments, object_id, combined_index_doc, doc):
        enrichments.update(self._perform_ner(object_id, combined_index_doc))
        return enrichments
