import time
import requests
import os
import redis
import json
from messages import save_message

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
REDIS_HOST = os.environ.get('REDIS_HOST')


def get_channel_message(channel_id, offset):
    message = requests.get(f'https://api.telegram.org/bot{API_KEY}/getUpdates?offset={offset}').json()
    if 'result' not in message or not message['result']:
        return []

    return [m for m in message['result'] if 'message' in m and m['message']['chat']['id'] == channel_id]


def catch_messages(channel_id):
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    offset = r.get('MC_UPDATE_ID')
    if not offset:
        offset = 0
    else:
        offset = int(offset)+1

    message = get_channel_message(channel_id, offset)
    for m in message:
        save_message(m)
        r.set('MC_UPDATE_ID', m['update_id'])

        logger.info("Catch message: " + json.dumps(m['message'], ensure_ascii=False))


while True:
    try:
        catch_messages(CHAT_ID)
    except Exception:
        logger.exception("message")
        time.sleep(60)

    time.sleep(10)