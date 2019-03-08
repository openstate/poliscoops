class_labels = ['good', 'bad']

def featurize(poliflw_obj):
    result = []

    data2feature = {
        u'source': [u'Partij nieuws', u'Facebook']
    }

    for f in data2feature.keys():
        result.append(data2feature[f].index(poliflw_obj[f]))

    result.append(len(poliflw_obj.get(u'description', u'')))

    return result
