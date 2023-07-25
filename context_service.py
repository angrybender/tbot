from elasticsearch import Elasticsearch
import os

ES_CA = '~/.elasticsearch/root.crt'
ES_USER = 'admin'
ES_PASS = 'adminadmin'
ES_HOSTS = [
    os.environ.get('ES_HOST')
]


def get_context(q, limit):
    conn = Elasticsearch(
        ES_HOSTS,
        http_auth=(ES_USER, ES_PASS),
        use_ssl=True,
        verify_certs=True,
        ca_certs=ES_CA)

    article = conn.search(index='wiki_1', query={
        'match': {
            'text': q.strip()
        }
    }, size=limit * 2)
    return list(set([_['_source']['text'] for _ in article['hits']['hits']]))[:limit]
