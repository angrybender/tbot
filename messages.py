import json
import os
import redis

API_KEY = os.environ.get('API_KEY')
CHAT_ID = int(os.environ.get('CHAT_ID'))
REDIS_HOST = os.environ.get('REDIS_HOST')


def read_history():
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    messages_ids = r.keys('MC_MESSAGES.*')

    messages = []
    for r_id in messages_ids:
        message = r.get(r_id).decode('utf')
        message = json.loads(message)
        messages.append(message)

    messages = sorted(messages, key=lambda m: m['update_id'])
    return list(messages)


def save_message(message):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    r.set('MC_MESSAGES.' + str(message['update_id']), json.dumps(message))
    r.expire('MC_MESSAGES.' + str(message['update_id']), 3600*3)
