import string

import bleach
from bleach.sanitizer import Cleaner
from html5lib.filters.base import Filter

class_labels = ['good', 'bad']


def html_cleanup(s):
    ATTRS = {
    }
    TAGS = []
    cleaner = Cleaner(
        tags=TAGS, attributes=ATTRS, filters=[Filter], strip=True)
    try:
        return cleaner.clean(s).replace('&amp;nbsp;', '')
    except TypeError:
        return u''


def featurize(poliflw_obj):
    result = []

    # features used:
    # 1. source (Ie. website or facebook)
    # 2. if there is an external link (In the case of facebook)
    # 3. the length of the clean version of the post
    # 4. the length of the uncleaned post
    # 5. the number of paragraphs
    # 6. the number of double enters (Ie. paragraphs when there is no html)

    data2feature = {
        u'source': [u'Partij nieuws', u'Facebook']
    }

    desc = poliflw_obj.get(u'description', u'')

    if u'<div class="facebook-external-link">' in desc:
        facebook_external = 1
    else:
        facebook_external = 0
    result.append(facebook_external)

    for f in data2feature.keys():
        result.append(data2feature[f].index(poliflw_obj[f]))

    clean_desc = html_cleanup(desc)
    result.append(len(clean_desc))
    result.append(len(desc))

    result.append(desc.lower().count('<p>'))
    result.append(desc.count("\n\n"))
    return result
