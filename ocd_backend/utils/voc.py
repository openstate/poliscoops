from urlparse import urljoin
from hashlib import sha1

class VocabularyMixin(object):
    """
    Interface for getting identifiers from vocabulary
    """

    def get_identifier(self, entity, identifier, ns='https://www.poliflw.nl/ns/voc/', additional={}):
        identifier_key = identifier
        if len(additional.keys()) > 0:
            identifier_additional = u'&'.join(['%s=%s' % (k, additional[k],) for k in additional.keys()])
            identifier_key += u'|' + identifier_additional
        identifier_hash = sha1(identifier_key.decode('utf8')).hexdigest()
        return urljoin(urljoin(ns, entity + '/'), identifier_hash)

    def get_organization(self, identifier, additional={}):
        additional['location'] = self.source_definition.get('Location', u'NL')
        return {
            "@type": u"Organization",
            "name": identifier,
            "@id": self.get_identifier(
                'Organization', identifier, additional=additional)
        }
