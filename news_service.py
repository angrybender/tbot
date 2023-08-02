from rss_parser import Parser
from requests import get
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import random

rss_urls = [
    'https://lenta.ru/rss/top7',
    'https://www.ixbt.com/export/news.rss',
]


def get_latest_news():
    output = []
    for rss_url in rss_urls:

        try:
            response = get(rss_url, timeout=10)
            rss = Parser.parse(response.text)
        except:
            continue

        current_date = datetime.now() - timedelta(days=1)
        current_date = current_date.strftime('%Y-%m-%d')

        for item in rss.channel.items:
            date_object = datetime.strptime(str(item.pub_date), "%a, %d %b %Y %H:%M:%S %z")
            date_object = date_object.strftime('%Y-%m-%d')

            description = BeautifulSoup(str(item.description), 'html.parser').text
            if date_object > current_date and description != 'None':
                output.append({'text': str(item.title) + "\n" + description, 'url': str(item.link)})

    random.shuffle(output)
    return output
