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


def save_message(message, processed=False):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    if processed:
        message['BOT:processed'] = True

    r.set('MC_MESSAGES.' + str(message['update_id']), json.dumps(message))
    r.expire('MC_MESSAGES.' + str(message['update_id']), 3600*3)


def save_chat_sequence(parent_id, message_id, message_text):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    sequence = _get_chat_sequence_by_parent_id(parent_id)
    if not sequence:
        sequence = []

    sequence.append({'id': message_id, 'text': message_text.strip()})

    r.set('MC_CHAT_SEQUENCE.' + str(parent_id), json.dumps(sequence))
    r.expire('MC_CHAT_SEQUENCE.' + str(parent_id), 3600)

    r.set('MC_CHAT_SEQUENCE_INDEX.' + str(message_id), json.dumps({'parent_id': parent_id}))
    r.expire('MC_CHAT_SEQUENCE_INDEX.' + str(message_id), 3600)


def _get_chat_sequence_by_parent_id(parent_id):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    sequence = r.get('MC_CHAT_SEQUENCE.' + str(parent_id))
    if not sequence:
        return []

    return json.loads(sequence.decode('utf'))


def find_chat_sequence_by_message(message_id):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    parent = r.get('MC_CHAT_SEQUENCE_INDEX.' + str(message_id))
    if not parent:
        return []

    parent = json.loads(parent.decode('utf'))
    parent_id = parent['parent_id']

    return _get_chat_sequence_by_parent_id(parent_id)
