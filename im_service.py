import requests
import os

API_KEY = os.environ.get('API_KEY')


def get_channel_message(channel_id, offset):
    message = requests.get(f'https://api.telegram.org/bot{API_KEY}/getUpdates?offset={offset}').json()
    if 'result' not in message or not message['result']:
        return []

    return [m for m in message['result'] if 'message' in m and m['message']['chat']['id'] == channel_id]


def send_message(channel_id, text):
    text = text.strip()
    result = requests.post(f'https://api.telegram.org/bot{API_KEY}/sendMessage?chat_id={channel_id}&text={text}').json()
    return result['result']['message_id'] if result['ok'] else -1


def send_typing(channel_id):
    requests.post(f'https://api.telegram.org/bot{API_KEY}/sendChatAction?chat_id={channel_id}&action=typing')