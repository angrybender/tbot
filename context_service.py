# from elasticsearch import Elasticsearch
from opensearchpy import OpenSearch
import os

# ES_CA = '~/.elasticsearch/root.crt'
# ES_USER = 'admin'
# ES_PASS = 'adminadmin'
# ES_HOSTS = [
#     os.environ.get('ES_HOST')
# ]

OS_CA = '~/.elasticsearch/root.crt'
OS_USER = 'admin'
OS_PASS = 'adminadmin'
OS_HOSTS = [
    os.environ.get('ES_HOST')
]


def get_connection():
    return OpenSearch(OS_HOSTS, http_auth=('admin', OS_PASS), use_ssl=True, verify_certs=True, ca_certs=OS_CA)


def get_context(q, limit):
    conn = get_connection()

    article = conn.search(index='wiki_1', body={
        'query': {
            'match': {
                'text': q.strip()
            }
        },
        'size': limit * 2
    })
    return list(set([_['_source']['text'] for _ in article['hits']['hits']]))[:limit]


def get_status():
    try:
        conn = get_connection()
        return conn.count(index='wiki_1').get('count', -1)
    except:
        return -1