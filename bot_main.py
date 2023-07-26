from messages import read_history, save_message, save_chat_sequence, find_chat_sequence_by_message
from nlu_engine import generate_message
from formatter_output import process_reply, preprocess_messages
import requests
import os
import time
import random

import logging
from sys import stdout

# Define logger
logger = logging.getLogger('BOT')

logger.setLevel(logging.INFO) # set logger level
logFormatter = logging.Formatter("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

API_KEY = os.environ.get('API_KEY')
CHAT_ID = int(os.environ.get('CHAT_ID'))
MY_NAME = os.environ.get('MY_NAME')
TIME_IDLE_THRESHOLD = [3600, 3600*3]
MESSAGES_CLUSTER_THRESHOLD = 60
SCORE_REPLY_THRESHOLD = 0.75
MIN_POST_REPLY_WORDS = 10

WAIT_TO_POST_COMMENT = {}
WAIT_TO_POST_COMMENT['value'] = random.randint(TIME_IDLE_THRESHOLD[0], TIME_IDLE_THRESHOLD[1])


def send_message(text):
    text = text.strip()
    result = requests.post(f'https://api.telegram.org/bot{API_KEY}/sendMessage?chat_id={CHAT_ID}&text={text}').json()
    return result['result']['message_id'] if result['ok'] else -1


def progress_cb(epoch, attempt):
    requests.post(f'https://api.telegram.org/bot{API_KEY}/sendChatAction?chat_id={CHAT_ID}&action=typing')


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

    is_mention_reply = False
    for message in messages:
        source_message = message

        message = message['message']
        post = message.get('text', '')
        chat_sequence = []
        if len(post) < 3:
            continue

        is_mention = False
        reply_to_my_message_id = 0
        if 'reply_to_message' in message \
                and message['reply_to_message']['from']['is_bot'] \
                and message['reply_to_message']['from']['username'] == MY_NAME:

            reply_to_my_message_id = message['reply_to_message']['message_id']
            is_mention = True
        elif post.find('@' + MY_NAME) == 0:
            post = ' '.join(post.split(' ')[1:])
            is_mention = True

        reply_message = ''
        if is_mention:
            logger.info("Reply to mention")

            # find chat:
            chat_sequence = find_chat_sequence_by_message(reply_to_my_message_id)
            saved_context = [preprocess_messages(m['text']) for m in chat_sequence]

            reply_message, reply_score = generate_message(saved_context, post, progress_cb)
            reply_message = process_reply(reply_message)

            message_prefix = '@' + message['from']['username']
            if reply_score < SCORE_REPLY_THRESHOLD:
                message_prefix += ' (я не уверен в релевантности ответа)\n'

            reply_message = message_prefix + ' ' + reply_message

        if reply_message:
            answer_id = send_message(reply_message)

            source_message['BOT:processed'] = True
            save_message(source_message)

            save_chat_sequence(chat_sequence[0]['id'] if chat_sequence else message['message_id'], message['message_id'], post)
            save_chat_sequence(chat_sequence[0]['id'] if chat_sequence else message['message_id'], answer_id, reply_message)

            is_mention_reply = True

    if is_mention_reply:
        return

    if not source_messages:
        return

    # comment last post:
    last_post = source_messages[-1]
    if time.time() - last_post['message']['date'] >= WAIT_TO_POST_COMMENT['value'] and not last_post.get('BOT:processed', False):
        post = group_user_messages(messages, last_post)
        if len(post.split()) < MIN_POST_REPLY_WORDS:
            return

        logger.info("Comment post")
        reply_message, reply_score = generate_message([], post)
        if reply_score < SCORE_REPLY_THRESHOLD:
            logger.info("Score too low: " + str(reply_score))
            return

        reply_message = '>>> ' + post[:40] + '...\n' + reply_message
        send_message(reply_message)
        last_post['BOT:processed'] = True
        save_message(last_post)

        WAIT_TO_POST_COMMENT['value'] = random.randint(TIME_IDLE_THRESHOLD[0], TIME_IDLE_THRESHOLD[1])
        logger.info("Sleep for " + str(WAIT_TO_POST_COMMENT['value']))


while True:
    try:
        main_cycle()
    except Exception:
        logger.exception("message")
        time.sleep(30)

    time.sleep(5)