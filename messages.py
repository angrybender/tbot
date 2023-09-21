from redis_service import get_items_by_query, save_item, get_by_key

_MESSAGE_HISTORY_TTL = 86400


def read_history():
    messages = get_items_by_query('MC_MESSAGES.*')
    messages = sorted(messages, key=lambda m: m['update_id'])
    return list(messages)


def save_message(message, processed=False):
    if processed:
        message['BOT:processed'] = True
    save_item(message, 'MC_MESSAGES.' + str(message['update_id']), _MESSAGE_HISTORY_TTL)


def save_chat_sequence(parent_id, message_id, message_text):
    sequence = _get_chat_sequence_by_parent_id(parent_id)
    if not sequence:
        sequence = []

    sequence.append({'id': message_id, 'text': message_text.strip()})

    save_item(sequence, 'MC_CHAT_SEQUENCE.' + str(parent_id), _MESSAGE_HISTORY_TTL)
    save_item({'parent_id': parent_id}, 'MC_CHAT_SEQUENCE_INDEX.' + str(message_id), _MESSAGE_HISTORY_TTL)


def _get_chat_sequence_by_parent_id(parent_id):
    sequence = get_by_key('MC_CHAT_SEQUENCE.' + str(parent_id))
    if not sequence:
        return []
    else:
        return sequence


def find_chat_sequence_by_message(message_id):
    parent = get_by_key('MC_CHAT_SEQUENCE_INDEX.' + str(message_id))
    if not parent:
        return []

    parent_id = parent['parent_id']
    return _get_chat_sequence_by_parent_id(parent_id)
