import feedparser
from requests import get
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

rss_urls = [
    #'https://www.cnews.ru/inc/rss/news.xml',
    #'https://www.ixbt.com/export/news.rss',
    'https://vc.ru/rss',
    'https://dtf.ru/rss',
]


def get_latest_news():
    output = []
    for rss_url in rss_urls:

        try:
            response = get(rss_url, timeout=10)
            rss = feedparser.parse(response.text)
        except:
            continue

        current_date = datetime.now() - timedelta(days=1)
        current_date = current_date.strftime('%Y-%m-%d')

        for item in rss.entries:
            date_object = datetime.strptime(item['published'], "%a, %d %b %Y %H:%M:%S %z")
            date_object = date_object.strftime('%Y-%m-%d')

            description = BeautifulSoup(item['summary'], 'html.parser').text
            if date_object > current_date and description != 'None':
                title = item['title']
                if title[-1] != '.':
                    title += '.'
                output.append({'text': title + " " + description, 'url': str(item.link)})

    return output
