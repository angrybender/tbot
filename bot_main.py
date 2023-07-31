from messages import read_history, save_message, save_chat_sequence, find_chat_sequence_by_message
from nlu_engine import generate_comment_to_post, generate_answer_for_chat
from formatter_output import process_reply, preprocess_messages
import os
import time
import random
from urllib.parse import urlparse
from context_service import get_status
from im_service import send_message, send_typing
from site_parser import get_content

import logging
from sys import stdout

# Define logger
logger = logging.getLogger('BOT')
logger.setLevel(logging.INFO)
logFormatter = logging.Formatter("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

CHAT_ID = int(os.environ.get('CHAT_ID'))
TECH_CHAT_ID = int(os.environ.get('TECH_CHAT_ID'))
MY_NAME = os.environ.get('MY_NAME')
TIME_IDLE_THRESHOLD = [3600, 3600*3]
TIME_IDLE_THRESHOLD = [30, 31]
MESSAGES_CLUSTER_THRESHOLD = 60
SCORE_REPLY_THRESHOLD = 0.75
LEN_REPLY_THRESHOLD = 10
MIN_POST_REPLY_WORDS = 20

WAIT_TO_POST_COMMENT = {
    'value': random.randint(TIME_IDLE_THRESHOLD[0], TIME_IDLE_THRESHOLD[1])
}


def send_debug_message(text):
    text = text.strip()
    result = send_message(TECH_CHAT_ID, text)
    assert(result > 0)


def command_info():
    meminfo = dict((i.split()[0].rstrip(':'),int(i.split()[1])) for i in open('/proc/meminfo').readlines())
    total_mem_gib = round(meminfo['MemTotal'] / (1024. ** 2), 1)
    free_mem_gib = round(meminfo['MemAvailable'] / (1024. ** 2), 1)

    message_lines = []
    if os.environ.get('DEBUG'):
        message_lines.append("Режим отладки")
    else:
        message_lines.append("Модель загружена")

    message_lines += [
        f"Общий объем памяти в системе: {total_mem_gib}Gb",
        f"Свободно памяти в системе: {free_mem_gib}Gb"
    ]

    antology_size = get_status()
    if antology_size > 0:
        message_lines.append(f"В антологии загружено статей: {antology_size}")
    else:
        message_lines.append("Ошибка загрузки антологии!")

    send_message(CHAT_ID, "\n".join(message_lines))


def is_reply(message: dict):
    if 'reply_to_message' in message \
            and message['reply_to_message']['from']['is_bot'] \
            and message['reply_to_message']['from']['username'] == MY_NAME:
        return True
    else:
        return False


def is_mention(message: dict):
    post = message.get('text', '')
    return post.find('@' + MY_NAME) == 0


def is_post_link(message: str):
    message = message.strip()

    logger.info("is_post_link: " + message)

    try:
        result = urlparse(message)
        return all([result.scheme, result.netloc])
    except:
        return False

def progress_cb(epoch, attempt):
    send_typing(CHAT_ID)


def group_user_messages(messages, start_message):
    if 'message' not in start_message:
        return ''

    base_date = start_message['message']['date']
    base_user = start_message['message']['from']['username']
    cluster = []
    for m in messages:
        if 'message' not in m:
            continue

        m = m['message']
        if m.get('from', {}).get('username', '') == base_user and base_date - m['date'] <= MESSAGES_CLUSTER_THRESHOLD:
            cluster.append(preprocess_messages(m.get('text', '')))

    return ' '.join(cluster)


def main_cycle():
    source_messages = read_history()
    messages = [m for m in source_messages if not m.get('BOT:processed', False)]

    is_chat_processed = False
    for message in messages:
        source_message = message

        message = message['message']
        post = message.get('text', '')

        if len(post) < 3:
            continue

        is_mention_flag = False
        reply_to_my_message_id = 0

        if is_reply(message):
            reply_to_my_message_id = message['reply_to_message']['message_id']
            is_mention_flag = True
        elif is_mention(message):
            post = ' '.join(post.split(' ')[1:])
            is_mention_flag = True

        message_processed = False
        if is_mention_flag and post.strip() == 'info':
            command_info()
            message_processed = True
        elif is_mention_flag:
            logger.info("Reply to mention")

            # find chat:
            chat_sequence = find_chat_sequence_by_message(reply_to_my_message_id)
            saved_context = [preprocess_messages(m['text']) for m in chat_sequence]

            try:
                reply_message, reply_score = generate_answer_for_chat(saved_context, post, progress_cb)
            except Exception as e:
                save_message(source_message, True)
                raise e

            reply_message = process_reply(reply_message)

            message_prefix = '@' + message['from']['username']
            if reply_score < SCORE_REPLY_THRESHOLD:
                message_prefix += ' (я не уверен в релевантности ответа)\n'
            raw_reply_message = reply_message
            reply_message = message_prefix + ' ' + reply_message

            answer_id = send_message(CHAT_ID, reply_message)

            msgid = chat_sequence[0]['id'] if chat_sequence else message['message_id']
            save_chat_sequence(msgid, message['message_id'], post)
            save_chat_sequence(msgid, answer_id, raw_reply_message)
            message_processed = True

        if message_processed:
            save_message(source_message, True)
            is_chat_processed = True

    if is_chat_processed or not source_messages:
        return

    # comment last post:
    last_post = source_messages[-1]
    if time.time() - last_post['message']['date'] >= WAIT_TO_POST_COMMENT['value'] and not last_post.get('BOT:processed', False):
        post = group_user_messages(messages, last_post)

        logger.info("POST:" + post)

        if is_post_link(post):
            logger.info("Try to fetch URI content...")
            post = get_content(post.strip())

        if len(post.split()) < MIN_POST_REPLY_WORDS:
            return

        logger.info("Comment post")
        reply_message, reply_score = generate_comment_to_post(post)
        if reply_score < SCORE_REPLY_THRESHOLD or len(reply_message.split()) < LEN_REPLY_THRESHOLD:
            logger.info("Score too low: " + str(reply_score))
        else:
            reply_message = '>>> ' + post[:40] + '...\n' + reply_message
            send_message(CHAT_ID, reply_message)

        save_message(last_post, True)

        WAIT_TO_POST_COMMENT['value'] = random.randint(TIME_IDLE_THRESHOLD[0], TIME_IDLE_THRESHOLD[1])
        logger.info("Sleep for " + str(WAIT_TO_POST_COMMENT['value']))


send_debug_message("INFO: Я готов!")
last_send_error = ''
while True:
    try:
        main_cycle()
    except Exception as e:
        current_error = str(e)
        if current_error != last_send_error:
            send_debug_message("ERROR: \n" + current_error)
            last_send_error = current_error

        logger.exception("message")
        time.sleep(30)

    time.sleep(5)