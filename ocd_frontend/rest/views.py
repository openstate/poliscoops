import copy
from datetime import datetime
import glob
from flask import (
    Blueprint, current_app, request, jsonify, redirect, url_for,)
from elasticsearch import NotFoundError
import os
from urlparse import urljoin
import sys

from ocd_frontend import thumbnails
from ocd_frontend import settings
from ocd_frontend.rest import OcdApiError, decode_json_post_data
from ocd_frontend.rest import tasks

bp = Blueprint('api', __name__)


def validate_from_and_size(data):
    # Check if 'size' was specified, if not, fallback to default
    try:
        n_size = int(
            data.get('size', current_app.config['DEFAULT_SEARCH_SIZE']))
    except ValueError:
        raise OcdApiError('Invalid value for \'size\'', 400)
    if n_size < 0 or n_size > current_app.config['MAX_SEARCH_SIZE']:
        raise OcdApiError('Value of \'size\' must be between 0 and %s' %
                          current_app.config['MAX_SEARCH_SIZE'], 400)

    # Check if 'from' was specified, if not, fallback to zero
    try:
        n_from = int(data.get('from', 0))
    except ValueError:
        raise OcdApiError('Invalid value for \'from\'', 400)
    if n_from < 0:
        raise OcdApiError('Value of \'from\' must 0 or larger', 400)

    return n_from, n_size


def parse_search_request(data, doc_type, mlt=False):
    print >>sys.stderr, data
    # Return an error when no query or an empty query string is provied
    query = data.get('query', None)

    scroll = data.get('scroll', None)
    scroll_id = data.get('scroll_id', None)
    # expansions:  /v0/search?expansions=2 or {"expansions": 2} when POSTing
    expansions = int(data.get('expansions', '0'))
    print >>sys.stderr, "Expansions: %s" % (expansions,)
    # if not query and not mlt:
    #     raise OcdApiError('Missing \'query\'', 400)

    # Additional fields requested to include in the response
    include_fields = [
        f.strip() for f in data.get('include_fields', []) if f.strip()]

    n_from, n_size = validate_from_and_size(data)

    # Check if 'sort' was specified, if not, fallback to '_score'
    sort = data.get('sort', '_score')
    if sort not in current_app.config['SORTABLE_FIELDS'][doc_type]:
        raise OcdApiError(
            'Invalid value for \'sort\', sortable fields are: %s'
            % ', '.join(current_app.config['SORTABLE_FIELDS'][doc_type]), 400)

    # Check if 'order' was specified, if not, fallback to desc
    order = data.get('order', 'desc')
    if order not in ['asc', 'desc']:
        raise OcdApiError(
            'Invalid value for \'order\', must be asc or desc', 400)

    # Check which 'facets' are requested
    req_facets = data.get('facets', {})
    if type(req_facets) is not dict:
        raise OcdApiError('\'facets\' should be an object', 400)

    facets = {}
    available_facets = copy.deepcopy(
        current_app.config['AVAILABLE_FACETS'][doc_type])
    available_facets.update(current_app.config['COMMON_FACETS'])

    # Inspect all requested facets and override the default settings
    # where necessary
    for facet, facet_opts in req_facets.iteritems():
        if facet not in available_facets:
            raise OcdApiError('\'%s\' is not a valid facet' % facet, 400)

        if type(facet_opts) is not dict:
            raise OcdApiError('\'facets.%s\' should cotain an object' % facet,
                              400)

        # Take the default facet options from the settings
        facets[facet] = available_facets[facet]
        f_type = facets[facet].keys()[0]
        if f_type == 'terms':
            if 'size' in facet_opts.keys():
                size = facet_opts['size']
                if type(size) is not int:
                    raise OcdApiError('\'facets.%s.size\' should be an '
                                      'integer' % facet, 400)

                facets[facet][f_type]['size'] = size

            if 'order' in facet_opts.keys():
                facets[facet][f_type]['order'] = facet_opts['order']
        elif f_type == 'date_histogram':
            if 'interval' in facet_opts.keys():
                interval = facet_opts['interval']
                if type(interval) is not unicode:
                    raise OcdApiError('\'facets.%s.interval\' should be '
                                      'a string' % facet, 400)

                if interval not in current_app.config[
                    'ALLOWED_DATE_INTERVALS'
                ]:
                    raise OcdApiError('\'%s\' is an invalid interval for '
                                      '\'facets.%s.interval\''
                                      % (interval, facet), 400)

                facets[facet][f_type]['interval'] = interval
            if 'order' in facet_opts.keys():
                facets[facet][f_type]['order'] = facet_opts['order']

    # Check which 'filters' are requested
    requested_filters = data.get('filters', {})
    if type(requested_filters) is not dict:
        raise OcdApiError('\'filters\' should be an object', 400)

    filters = []
    # Inspect all requested filters and add them to the list of filters
    for r_filter, filter_opts in requested_filters.iteritems():
        # Use facet definitions to check if the requested filter can be used
        if r_filter not in available_facets:
            raise OcdApiError('\'%s\' is not a valid filter' % r_filter, 400)

        f_type = available_facets[r_filter].keys()[0]
        if f_type == 'terms':
            if 'terms' not in filter_opts:
                raise OcdApiError(
                    'Missing \'filters.%s.terms\'' % r_filter, 400)

            if type(filter_opts['terms']) is not list:
                raise OcdApiError('\'filters.%s.terms\' should be an array'
                                  % r_filter, 400)

            # Check the type of each item in the list
            for term in filter_opts['terms']:
                if type(term) is not unicode and type(term) is not int:
                    raise OcdApiError('\'filters.%s.terms\' should only '
                                      'contain strings and integers'
                                      % r_filter, 400)

            filters.append({
                'terms': {
                    available_facets[r_filter]['terms']['field']: filter_opts[
                        'terms']
                }
            })
        elif f_type == 'date_histogram':
            if type(filter_opts) is not dict:
                raise OcdApiError('\'filters.%s\' should be an object'
                                  % r_filter, 400)

            field = available_facets[r_filter]['date_histogram']['field']
            r_filter = {'range': {field: {}}}

            if 'from' in filter_opts:
                r_filter['range'][field]['from'] = filter_opts['from']

            if 'to' in filter_opts:
                r_filter['range'][field]['to'] = filter_opts['to']

            filters.append(r_filter)
        else:
            if type(filter_opts) is not dict:
                raise OcdApiError('\'filters.%s\' should be an object'
                                  % r_filter, 400)
            filters.append(filter_opts)

    filters.append({"term": {"hidden": "false"}})

    return {
        'query': query,
        'n_size': n_size,
        'n_from': n_from,
        'sort': sort,
        'order': order,
        'facets': facets,
        'filters': filters,
        'include_fields': include_fields,
        'scroll': scroll,
        'scroll_id': scroll_id,
        'expansions': expansions
    }


def format_search_aggregations(aggregations):
    output = {
        "ibmsc:facets": []
    }
    for a_name in aggregations.keys():
        result = {
            "ibmsc:taxonomyId": None,
            "ibmsc:facet": {
                # "@id": a_name.capitalize(),
                "dc:title": a_name.capitalize(),
                "ibmsc:facetValue": []
            }
        }
        bucket_ids = []
        for b in aggregations[a_name].get('buckets', []):
            result['ibmsc:facet']['ibmsc:facetValue'].append({
                 #'@id': b['key'],
                 'dc:title': b.get('key_as_string', b['key']),
                 'ibmsc:label': b['key'],
                 'ibmsc:weight': b['doc_count']
            })
            bucket_ids += find_ids_in_item(b)
        print >>sys.stderr, "bucket ids: %s" % (bucket_ids,)
        if len(bucket_ids) > 0:
            bucket_expanded = get_objects_for_ids(bucket_ids)
            for b in result['ibmsc:facet']['ibmsc:facetValue']:
                b['as:object'] = bucket_expanded[b['ibmsc:label']]
        output["ibmsc:facets"].append(result)
    return output

def find_ids_in_item(item):
    result = []
    for k, v in item.iteritems():
        if k == '@id':
            continue
        if type(v) is list:
            result += [x for x in v if '/ns/voc/' in x]
        elif isinstance(v, basestring) and '/ns/voc/' in v:
            result.append(v)
    return list(set(result))

def get_objects_for_ids(ids):
    es_q = {
        "query": {
            "bool": {
                "filter": {
                    "terms": {
                        "item.@id.raw": ids
                    }
                }
            }
        },
        "size": 500
    }

    es_r = current_app.es.search(body=es_q)
    return {e['_source']['item']['@id']: e['_source']['item'] for e in es_r['hits']['hits']}

def expand_object(item, all_objects):
    for k, v in item.iteritems():
        if k in ['@id', 'href']:
            continue
        if type(v) is list:
            res = []
            for x in v:
                if isinstance(x, basestring) and '/ns/voc/' in x:
                    res.append(all_objects[x])
                else:
                    res.append(x)
            item[k] = res
        elif isinstance(v, basestring) and '/ns/voc/' in v:
            if v in all_objects:
                item[k] = expand_object(all_objects[v], all_objects)
    return item

def format_search_items(items, expansions=0):
    print >>sys.stderr, "Going for %s expansions" % (expansions,)

    if expansions == 0:
        return items

    cur_expansion = 0
    cur_items = items
    expanded_items = {}
    while cur_expansion < expansions:
        ids = []
        for i in cur_items:
            ids += find_ids_in_item(i)
        all_ids = list(set(ids))
        all_objects = get_objects_for_ids(all_ids)
        expanded_items.update(all_objects)
        print >>sys.stderr, "Expansion %s: %s" % (cur_expansion, all_objects.keys())
        cur_items = all_objects.values()
        cur_expansion += 1
    return [expand_object(i, expanded_items) for i in items]
    # return [expand_object(i, all_objects) for i in items]

def format_search_results(results, doc_type=u'item', expansions=0):
    del results['_shards']
    del results['timed_out']

    for hit in results['hits']['hits']:
        # del hit['_index']
        # del hit['_type']
        # del hit['_source']['hidden']
        kwargs = {
            'object_id': hit['_id'],
            'source_id': hit['_source']['meta']['source_id'],
            '_external': True,
            '_scheme': 'https'
        }
        hit['_source']['meta']['pfl_url'] = url_for('api.get_object', **kwargs)
        for key in current_app.config['EXCLUDED_FIELDS_ALWAYS']:
            try:
                del hit['_source'][key]
            except KeyError as e:
                pass

    # ibmsc from : https://www.ibm.com/support/knowledgecenter/en/SSYJ99_8.5.0/search-rest-api/facets-spec.html
    formatted_results = {
      "@context": {
        "as": "https://www.w3.org/ns/activitystreams#",
        "ibmsc": "http://www.ibm.com/search/content/2010#",
        "dc": "http://purl.org/dc/terms/"
      },
      "as:type": "CollectionPage",
      "as:items": [
      ],
      "as:totalItems": results['hits']['total']
    }

    search_items = []
    for hit in results['hits']['hits']:
        hit['_source']['item']['@context'] = "https://www.w3.org/ns/activitystreams"
        search_items.append(hit['_source']['item'])
    formatted_results["as:items"] = format_search_items(search_items, expansions)

    if results.has_key('aggregations'):
        formatted_results.update(format_search_aggregations(results['aggregations']))

    if '_scroll_id' in results:
        formatted_results['meta']['scroll'] = results['_scroll_id']

    return formatted_results

def validate_included_fields(include_fields, excluded_fields,
                             allowed_to_include):
    """
    Utility method that determines if the requested fields that the user wants
    to see included may actually be included.

    :param include_fields: Fields requested to be included
    :param excluded_fields: Fields that are excluded by default
    :param allowed_to_include: Fields that the user is allowed include
    :return:
    """
    for field in include_fields:
        if field and field in excluded_fields and field in allowed_to_include:
            excluded_fields.remove(field)
    return excluded_fields


def format_sources_results(results):
    sources = []

    for bucket in results['aggregations']['index']['buckets']:
        source = {d['key']: d['doc_count'] for d in bucket['doc_type']['buckets']}
        source['id'] = u'_'.join(bucket['key'].split('_')[1:-1])

        # FIXME: quick hack
        if source['id'] == u'combined':
            source['id'] = u'combined_index'

        sources.append(source)

    return {
        'sources': sources
    }


# Retrieve the indices/sources and the total number of documents per
# type (counting only documents which are not hidden!)
@bp.route('/sources', methods=['GET'])
def list_sources():
    es_q = {
        'query': {
            "bool": {
                "must": {
                    "term": {"hidden": False}
                }
            }
        },
        'aggregations': {
            'index': {
                'terms': {
                    'field': '_index',
                    'size': 100000
                },
                'aggregations': {
                    'doc_type': {
                        'terms': {
                            'field': '_type',
                            'size': 100000
                        }
                    }
                }
            }
        },
        "size": 0
    }

    es_r = current_app.es.search(body=es_q)

    # Log a 'sources' event if usage logging is enabled
    if current_app.config['USAGE_LOGGING_ENABLED']:
        tasks.log_event.delay(
            user_agent=request.user_agent.string,
            referer=request.headers.get('Referer', None),
            user_ip=request.remote_addr,
            created_at=datetime.utcnow(),
            event_type='sources',
            query_time_ms=es_r['took']
        )

    return jsonify(format_sources_results(es_r))


@bp.route('/search', methods=['POST', 'GET'])
@bp.route('/search/<doc_type>', methods=['POST', 'GET'])
@decode_json_post_data
def search(doc_type=u'item'):
    data = request.data or request.args
    search_req = parse_search_request(data, doc_type)
    print >>sys.stderr, search_req

    excluded_fields = validate_included_fields(
        include_fields=search_req['include_fields'],
        excluded_fields=current_app.config['EXCLUDED_FIELDS_SEARCH'],
        allowed_to_include=current_app.config['ALLOWED_INCLUDE_FIELDS_SEARCH']
    )

    # the fields we want to highlight in the Elasticsearch response
    highlighted_fields = current_app.config['COMMON_HIGHLIGHTS']
    highlighted_fields.update(
        current_app.config['AVAILABLE_HIGHLIGHTS'][doc_type])

    # Construct the query we are going to send to Elasticsearch
    es_q = {
        'query': {
            'bool': {
                'must': {
                    'simple_query_string': {
                        'query': search_req['query'],
                        'default_operator': 'AND',
                        'fields':current_app.config[
                            'SIMPLE_QUERY_FIELDS'][doc_type]
                    }
                },
                'filter': {}
            }
        },
        'aggregations': search_req['facets'],
        'size': search_req['n_size'],
        'from': search_req['n_from'],
        'sort': {
            search_req['sort']: {'order': search_req['order']}
        },
        '_source': {
            'excludes': excluded_fields
        },
        'highlight': {
            'fields': highlighted_fields
        }
    }

    if not search_req['query']:
        es_q['query']['bool']['must'] = {'match_all': {}}

    if search_req['filters']:
        es_q['query']['bool']['filter'] = search_req['filters']

    if doc_type != settings.DOC_TYPE_DEFAULT:
        request_doc_type = doc_type
    else:
        request_doc_type = None

    print >>sys.stderr, es_q
    es_r = current_app.es.search(body=es_q,
                                 index=current_app.config['COMBINED_INDEX'],
                                 doc_type=request_doc_type)
    scroll = search_req['scroll']
    scroll_id = search_req['scroll_id']
    if scroll is not None:
        if scroll_id is None:
            es_r = current_app.es.search(
                body=es_q,
                index=current_app.config['COMBINED_INDEX'],
                doc_type=request_doc_type, scroll=scroll)
            scroll_id = es_r['_scroll_id']
        es_r = current_app.es._es.scroll(scroll=scroll, scroll_id=scroll_id)
    else:
        es_r = current_app.es.search(
            body=es_q,
            index=current_app.config['COMBINED_INDEX'],
            doc_type=request_doc_type)

    # Log a 'search' event if usage logging is enabled
    if current_app.config['USAGE_LOGGING_ENABLED']:
        hit_log = []
        for hit in es_r['hits']['hits']:
            hit_log.append({
                'source_id': hit['_source']['meta']['source_id'],
                'object_id': hit['_id'],
                'score': hit['_score']
            })

        tasks.log_event.delay(
            user_agent=request.user_agent.string,
            referer=request.headers.get('Referer', None),
            user_ip=request.remote_addr,
            created_at=datetime.utcnow(),
            event_type='search',
            doc_type=doc_type,
            query=search_req,
            hits=hit_log,
            n_total_hits=es_r['hits']['total'],
            query_time_ms=es_r['took']
        )

    print >>sys.stderr, search_req['expansions']

    return jsonify(format_search_results(es_r, doc_type, search_req['expansions']))


@bp.route('/<source_id>/search', methods=['POST', 'GET'])
@bp.route('/<source_id>/<doc_type>/search', methods=['POST', 'GET'])
@decode_json_post_data
def search_source(source_id, doc_type=u'item'):
    # Disallow searching in multiple indexes by providing a wildcard
    if '*' in source_id:
        raise OcdApiError('Invalid \'source_id\'', 400)

    index_name = '%s_%s' % (current_app.config['DEFAULT_INDEX_PREFIX'], source_id)

    data = request.data or request.args
    search_req = parse_search_request(data, doc_type)

    excluded_fields = validate_included_fields(
        include_fields=search_req['include_fields'],
        excluded_fields=current_app.config['EXCLUDED_FIELDS_DEFAULT'],
        allowed_to_include=current_app.config['ALLOWED_INCLUDE_FIELDS_DEFAULT']
    )

    # Construct the query we are going to send to Elasticsearch
    es_q = {
        'query': {
            'bool': {
                'must': {
                    'simple_query_string': {
                        'query': search_req['query'],
                        'default_operator': 'AND',
                        'fields': current_app.config[
                            'SIMPLE_QUERY_FIELDS'][doc_type]
                        # 'fields': [
                        #     'title^3',
                        #     'authors^2',
                        #     'description^2',
                        #     'meta.original_object_id',
                        #     'all_text'
                        # ]
                    }
                },
                'filter': {}
            }
        },
        'aggregations': search_req['facets'],
        'size': search_req['n_size'],
        'from': search_req['n_from'],
        'sort': {
            search_req['sort']: {'order': search_req['order']}
        },
        '_source': {
            'excludes': excluded_fields
        }
    }

    if not search_req['query']:
        es_q['query']['bool']['must'] = {'match_all': {}}

    if search_req['filters']:
        es_q['query']['bool']['filter'] = search_req['filters']

    try:
        es_r = current_app.es.search(
            body=es_q, index=index_name, doc_type=doc_type)
    except NotFoundError:
        raise OcdApiError('Source \'%s\' does not exist' % source_id, 404)

    # Log a 'search' event if usage logging is enabled
    if current_app.config['USAGE_LOGGING_ENABLED']:
        hit_log = []
        for hit in es_r['hits']['hits']:
            hit_log.append({
                'source_id': hit['_source']['meta']['source_id'],
                'object_id': hit['_id'],
                'score': hit['_score']
            })

        tasks.log_event.delay(
            user_agent=request.user_agent.string,
            referer=request.headers.get('Referer', None),
            user_ip=request.remote_addr,
            created_at=datetime.utcnow(),
            event_type='search',
            source_id=source_id,
            doc_type=doc_type,
            query=search_req,
            hits=hit_log,
            n_total_hits=es_r['hits']['total'],
            query_time_ms=es_r['took']
        )

    return jsonify(format_search_results(es_r, doc_type))


@bp.route('/<source_id>/<object_id>', methods=['GET'])
@bp.route('/<source_id>/<doc_type>/<object_id>', methods=['GET'])
def get_object(source_id, object_id, doc_type=u'item'):
    index_name = '%s_%s' % (current_app.config['DEFAULT_INDEX_PREFIX'],
                            source_id)

    include_fields = [f.strip() for f in request.args.get('include_fields', '').split(',') if f.strip()]

    excluded_fields = validate_included_fields(
        include_fields=include_fields,
        excluded_fields=current_app.config['EXCLUDED_FIELDS_DEFAULT'],
        allowed_to_include=current_app.config['ALLOWED_INCLUDE_FIELDS_DEFAULT']
    )

    try:
        obj = current_app.es.get(index=index_name, id=object_id,
                                 doc_type=doc_type,
                                 _source_exclude=excluded_fields)
    except NotFoundError, e:
        if e.error.startswith('IndexMissingException'):
            message = 'Source \'%s\' does not exist' % source_id
        else:
            message = 'Document not found.'

        raise OcdApiError(message, 404)

    # Log a 'get_object' event if usage logging is enabled
    if current_app.config['USAGE_LOGGING_ENABLED']:
        tasks.log_event.delay(
            user_agent=request.user_agent.string,
            referer=request.headers.get('Referer', None),
            user_ip=request.remote_addr,
            created_at=datetime.utcnow(),
            event_type='get_object',
            source_id=source_id,
            doc_type=doc_type,
            object_id=object_id
        )

    for key in current_app.config['EXCLUDED_FIELDS_ALWAYS']:
        try:
            del obj['_source'][key]
        except KeyError as e:
            pass

    return jsonify(obj['_source'])


@bp.route('/<source_id>/<object_id>/source')
@bp.route('/<source_id>/<doc_type>/<object_id>/source')
def get_object_source(source_id, object_id, doc_type=u'item'):
    index_name = '%s_%s' % (current_app.config['DEFAULT_INDEX_PREFIX'],
                            source_id)

    try:
        obj = current_app.es.get(index=index_name, id=object_id,
                                 doc_type=doc_type,
                                 _source_include=['source_data'])
    except NotFoundError, e:
        if e.error.startswith('IndexMissingException'):
            message = 'Source \'%s\' does not exist' % source_id
        else:
            message = 'Document not found.'

        raise OcdApiError(message, 404)

    resp = current_app.make_response(obj['_source']['source_data']['data'])
    resp.mimetype = obj['_source']['source_data']['content_type']

    # Log a 'get_object_source' event if usage logging is enabled
    if current_app.config['USAGE_LOGGING_ENABLED']:
        tasks.log_event.delay(
            user_agent=request.user_agent.string,
            referer=request.headers.get('Referer', None),
            user_ip=request.remote_addr,
            created_at=datetime.utcnow(),
            event_type='get_object_source',
            source_id=source_id,
            doc_type=doc_type,
            object_id=object_id
        )

    return resp


@bp.route('/<source_id>/<object_id>/stats')
@bp.route('/<source_id>/<doc_type>/<object_id>/stats')
def get_object_stats(source_id, object_id, doc_type=u'item'):
    index_name = '%s_%s' % (current_app.config['DEFAULT_INDEX_PREFIX'],
                            source_id)

    object_exists = current_app.es.exists(index=index_name, doc_type=doc_type,
                                          id=object_id)
    if not object_exists:
        raise OcdApiError('Document or source not found.', 404)

    queries = [
        (
            'n_appeared_in_search_results',
            'search',
            {
                "query": {
                    "constant_score": {
                        "filter": {
                            "term": {
                                "event_properties.hits.object_id": object_id
                            }
                        }
                    }
                }
            }
        ),
        (
            'n_appeared_in_similar_results',
            'similar',
            {
                "query": {
                    "constant_score": {
                        "filter": {
                            "term": {
                                "event_properties.hits.object_id": object_id
                            }
                        }
                    }
                }
            }
        ),
        (
            'n_get',
            'get_object',
            {
                "query": {
                    "constant_score": {
                        "filter": {
                            "term": {
                                "event_properties.object_id": object_id
                            }
                        }
                    }
                }
            }
        ),
        (
            'n_get_source',
            'get_object_source',
            {
                "query": {
                    "constant_score": {
                        "filter": {
                            "term": {
                                "event_properties.object_id": object_id
                            }
                        }
                    }
                }
            }
        )
    ]

    search_body = []

    for query in queries:
        search_body.append({
            'index': current_app.config['USAGE_LOGGING_INDEX'],
            'type': query[1],
            'size': 0
        })
        search_body.append(query[2])

    es_r = current_app.es.msearch(search_body)

    stats = {}
    for query_i, result in enumerate(es_r['responses']):
        stats[queries[query_i][0]] = result['hits']['total']

    return jsonify(stats)


@bp.route('/<source_id>/similar/<object_id>', methods=['POST'])
@bp.route('/similar/<object_id>', methods=['POST'])
@bp.route('/<source_id>/<doc_type>/similar/<object_id>', methods=['POST'])
@bp.route('/similar/<doc_type>/<object_id>', methods=['POST'])
@decode_json_post_data
def similar(object_id, source_id=None, doc_type=u'item'):
    search_params = parse_search_request(request.data, doc_type, mlt=True)
    # not relevant, as mlt already creates the query for us
    search_params.pop('query')

    if source_id:
        index_name = '%s_%s' % (current_app.config['DEFAULT_INDEX_PREFIX'],
                                source_id)
    else:
        index_name = current_app.config['COMBINED_INDEX']

    excluded_fields = validate_included_fields(
        include_fields=search_params['include_fields'],
        excluded_fields=current_app.config['EXCLUDED_FIELDS_DEFAULT'],
        allowed_to_include=current_app.config['ALLOWED_INCLUDE_FIELDS_DEFAULT']
    )

    # FIXME: should do here something with the fields ...
    es_q = {
        'query': {
            'bool': {
                'must': {
                    'more_like_this': {
                        'docs': [{
                            '_index': index_name,
                            '_type': doc_type,
                            '_id': object_id
                        }],
                        'fields': [
                            'title',
                            'authors',
                            'description',
                            'meta.original_object_id',
                            'all_text'
                        ]
                    }
                },
                'filter': {}
            }
        },
        'facets': search_params['facets'],
        'size': search_params['n_size'],
        'from': search_params['n_from'],
        'sort': {
            search_params['sort']: {'order': search_params['order']}
        },
        '_source': {
            'excludes': excluded_fields
        }
    }

    if search_params['filters']:
        es_q['query']['bool']['filter'] = search_params['filters']

    try:
        es_r = current_app.es.search(body=es_q, index=index_name,
                                     _source_exclude=excluded_fields)
    except NotFoundError:
        raise OcdApiError('Source \'%s\' does not exist' % source_id, 404)

    # Log a 'search_similar' event if usage logging is enabled
    if current_app.config['USAGE_LOGGING_ENABLED']:
        hit_log = []
        for hit in es_r['hits']['hits']:
            hit_log.append({
                'source_id': hit['_source']['meta']['source_id'],
                'object_id': hit['_id'],
                'score': hit['_score']
            })

        tasks.log_event.delay(
            user_agent=request.user_agent.string,
            referer=request.headers.get('Referer', None),
            user_ip=request.remote_addr,
            created_at=datetime.utcnow(),
            event_type='search_similar',
            similar_to_source_id=source_id,
            similar_to_object_id=object_id,
            doc_type=doc_type,
            query=search_params,
            hits=hit_log,
            n_total_hits=es_r['hits']['total'],
            query_time_ms=es_r['took']
        )

    return jsonify(format_search_results(es_r, doc_type))


@bp.route('/resolve/<url_id>', methods=['GET'])
def resolve(url_id):
    try:
        resp = current_app.es.get(index=current_app.config['RESOLVER_URL_INDEX'],
                                  doc_type='url', id=url_id)

        # If the media item is not "thumbnailable" (e.g. it's a video), or if
        # the user did not provide a content type, redirect to original source
        if resp['_source'].get('content_type', 'original') not in current_app.config['THUMBNAILS_MEDIA_TYPES']:
            # Log a 'resolve' event if usage logging is enabled
            if current_app.config['USAGE_LOGGING_ENABLED']:
                tasks.log_event.delay(
                    user_agent=request.user_agent.string,
                    referer=request.headers.get('Referer', None),
                    user_ip=request.remote_addr,
                    created_at=datetime.utcnow(),
                    event_type='resolve',
                    url_id=url_id,
                )
            return redirect(resp['_source']['original_url'])

        size = request.args.get('size', 'large')
        if size not in current_app.config['THUMBNAIL_SIZES']:
            available_formats = "', '".join(sorted(current_app.config['THUMBNAIL_SIZES'].keys()))
            msg = 'You did not provide an appropriate thumbnail size. Available ' \
                  'options are \'{}\''
            err_msg = msg.format(available_formats)

            if request.mimetype == 'application/json':
                raise OcdApiError(err_msg, 400)
            return '<html><body>{}</body></html>'.format(err_msg), 400

        thumbnail_path = thumbnails.get_thumbnail_path(url_id, size)
        if not os.path.exists(thumbnail_path):
            # Thumbnail does not exist yet, check of we've downloaded the
            # original already
            original = thumbnails.get_thumbnail_path(url_id, 'original')
            if not os.path.exists(original):
                # If we don't, fetch a copy of the original and store it in the
                # thumbnail cache, so we can use it as a source for thumbnails
                thumbnails.fetch_original(resp['_source']['original_url'], url_id)

            # Create the thumbnail with the requested size, and save it to the
            # thumbnail cache
            thumbnails.create_thumbnail(original, url_id, size)

        # Log a 'resolve_thumbnail' event if usage logging is enabled
        if current_app.config['USAGE_LOGGING_ENABLED']:
            tasks.log_event.delay(
                user_agent=request.user_agent.string,
                referer=request.headers.get('Referer', None),
                user_ip=request.remote_addr,
                created_at=datetime.utcnow(),
                event_type='resolve_thumbnail',
                url_id=url_id,
                requested_size=size
            )

        return redirect(thumbnails.get_thumbnail_url(url_id, size))

    except NotFoundError:
        if request.mimetype == 'application/json':
            raise OcdApiError('URL is not available; the source may no longer '
                              'be available', 404)

        return '<html><body>There is no original url available. You may '\
               'have an outdated URL, or the resolve id is incorrect.</body>'\
               '</html>', 404


@bp.route('/dumps', methods=['GET'])
def list_dumps():
    dump_list = glob.glob('%s/*/*.gz' % current_app.config.get('DUMPS_DIR'))
    dumps = {}

    for dump in dump_list:
        index_name, dump_file = dump.replace('%s/' % current_app.config
                                                 .get('DUMPS_DIR'), '')\
                                                 .split('/')
        if index_name not in dumps:
            dumps[index_name] = []
        dumps[index_name].append(urljoin(current_app.config['DUMP_URL'],
                                         dump_file))

    return jsonify({'dumps': dumps})
