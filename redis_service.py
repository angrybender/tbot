import json
import os
import redis

REDIS_HOST = os.environ.get('REDIS_HOST')


def get_items_by_query(query: str, parse_json=True) -> list:
    if query[-1] != '*':
        query += '*'

    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    items_ids = r.keys(query)
    output = []
    for r_id in items_ids:
        item = r.get(r_id)
        if parse_json:
            item = item.decode('utf')
            item = json.loads(item)

        output.append(item)
    return output


def save_item(item, key: str, ttl: int):
    assert ttl > 0
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    r.set(key, json.dumps(item))
    r.expire(key, ttl)


def get_by_key(key: str, parse_json=True):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    item = r.get(key)
    if not item:
        return None

    if parse_json:
        return json.loads(item.decode('utf'))
