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
from redis_service import save_item, get_by_key
from news_service import get_latest_news
from topic_model import get_top_similar_n
import datetime

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
TIME_IDLE_THRESHOLD = [int(_) for _ in os.environ.get('TIME_IDLE_THRESHOLD').split(',')]

NEWS_COMMENT_IDLE = int(os.environ.get('TIME_NEWS_COMMENT'))
assert NEWS_COMMENT_IDLE > 0

MESSAGES_CLUSTER_THRESHOLD = 60
SCORE_REPLY_THRESHOLD = 0.75
LEN_REPLY_THRESHOLD = 10
MIN_POST_REPLY_WORDS = 20
TOP_N_SIMILAR_NEWS = 5
TOP_N_HISTORY_POSTS = 10


def set_chat_activity_ttl():
    value = random.randint(TIME_IDLE_THRESHOLD[0], TIME_IDLE_THRESHOLD[1])
    save_item({
        'value': value
    }, 'WAIT_TO_POST_COMMENT', 86400)
    return value


def get_chat_activity_ttl():
    value = get_by_key('WAIT_TO_POST_COMMENT')
    if not value:
        return set_chat_activity_ttl()
    else:
        return value['value']


def get_last_news_comment():
    value = get_by_key('LAST_NEWS_COMMENT')
    if not value:
        return 0
    else:
        return value['value']


def set_last_news_comment(comment_time):
    save_item({'value': comment_time}, 'LAST_NEWS_COMMENT', NEWS_COMMENT_IDLE*2)



save_item({'value': time.time()}, 'TIME_BOT_STARTED', 86400)
def get_bot_started():
    value = get_by_key('TIME_BOT_STARTED')
    return value.get('value') if value else 0


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


def score_comment(text):
    words = text.lower().split()
    total_words = len(set(words))
    words_idx = {}
    for w in words:
        if w in words_idx:
            words_idx[w]+=1
        else:
            words_idx[w] = 1

    return sum(words_idx.values())/total_words


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

    if is_chat_processed:
        return

    # comment last post:
    if source_messages:
        last_post = source_messages[-1]
    else:
        last_post = None

    chat_last_activity = get_chat_activity_ttl()
    current_time = time.time()
    if last_post and \
            current_time - last_post['message']['date'] >= chat_last_activity \
            and not last_post.get('BOT:processed', False):
        post = group_user_messages(messages, last_post)

        if is_post_link(post):
            logger.info("Try to fetch URI content...")
            post = get_content(post.strip())

        if len(post.split()) >= MIN_POST_REPLY_WORDS:
            logger.info("Comment post")
            reply_message, reply_score = generate_comment_to_post(post)
            if reply_score < SCORE_REPLY_THRESHOLD or len(reply_message.split()) < LEN_REPLY_THRESHOLD:
                logger.info("Score too low: " + str(reply_score) + "\n" + reply_message)
            else:
                reply_message = '>>> ' + post[:80] + '...\n' + reply_message
                send_message(CHAT_ID, reply_message)

        save_message(last_post, True)

        time_sleep = set_chat_activity_ttl()
        logger.info(f"Sleep for {time_sleep}")

    # comment some news:
    last_news_comment_time = get_last_news_comment()
    if last_post:
        last_chat_activity_time = last_post['message']['date']
    else:
        last_chat_activity_time = get_bot_started()

    current_hour = datetime.datetime.now().time().hour
    if (current_hour >= 20 or current_hour <= 6) and \
            current_time - last_chat_activity_time > chat_last_activity and current_time - last_news_comment_time > NEWS_COMMENT_IDLE:

        all_possible_posts = (m['message'].get('text', '') for m in source_messages)
        all_possible_posts = [m for m in all_possible_posts]
        if len(all_possible_posts) == 0:
            return
        all_possible_posts = sorted(all_possible_posts, key=lambda m: -len(m))[:TOP_N_HISTORY_POSTS]

        logger.info("Trying to comment news, with: " + str(len(all_possible_posts)) + ' posts...')
        all_news = get_latest_news()
        top_n_news_i = get_top_similar_n(all_possible_posts, [n['text'] for n in all_news], TOP_N_SIMILAR_NEWS)

        for news_item_i in top_n_news_i:
            news_item = all_news[news_item_i]
            semaphore = f"NEWS_SEMAPHORE:{news_item['url']}"
            if get_by_key(semaphore):
                continue

            logger.info("Process new: " + news_item['text'][:40] + "...")
            reply_message, reply_score = generate_comment_to_post(news_item['text'], 0.5)
            if reply_score >= SCORE_REPLY_THRESHOLD and len(reply_message.split()) >= LEN_REPLY_THRESHOLD and score_comment(reply_message) < 1.8:
                send_message(CHAT_ID, reply_message + "\n" + news_item['url'])
                save_item({"processed": True}, semaphore, 864000)
                break

        set_last_news_comment(current_time)


send_debug_message(f"INFO: Я готов!\nРазброс времени ожидания: {TIME_IDLE_THRESHOLD[0]}...{TIME_IDLE_THRESHOLD[1]}\nПериод публикации новостей: {NEWS_COMMENT_IDLE}")
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