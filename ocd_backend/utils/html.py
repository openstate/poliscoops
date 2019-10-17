import re
from jparser import PageModel


class HTMLContentExtractionMixin(object):
    def extract_content(self, full_content, encoding):
        # TODO: Fix byte 0xff problem: 'utf8' codec can't decode byte 0xff in position <x>: invalid start byte
        # TODO: Fix Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
        # TODO: remove things like: Share on Facebook Share Share on Twitter Tweet Share on Pinterest Share Share on LinkedIn Share Send email Mail Print Print
        try:
            cleaned = PageModel(full_content.decode(encoding)).extract()
        except Exception as e:
            print >>sys.stderr, e
            cleaned = {}

        output = u''
        for elem in cleaned.get('content', []):
            if elem['type'] == 'text':
                # if it starts with these words it's probably garbage
                if re.match('^\s*(Share|Deel|Delen|Send|Print)\s*', elem['data']) is None:
                    output += '<p>%s</p>' % (elem['data'],)
            if elem['type'] == 'image':
                output += '<img src="%s" />' % (elem['data']['src'],)

        if output.strip() != u'':
            return unicode(output)
