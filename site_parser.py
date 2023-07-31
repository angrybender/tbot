import requests
from bs4 import BeautifulSoup


def get_content(url):
    try:
        html = requests.get(url).content

        soup = BeautifulSoup(html, 'html.parser')

        tags = soup.find_all('meta')

        text = []
        for tag in tags:
            name = tag.get_attribute_list('name')
            if name and name[0] and name[0].lower() == 'description':
                tag_content = tag.get_attribute_list('content')
                if tag_content and tag_content[0]:
                    text.append(tag_content[0].strip())

        tags = soup.find_all('title') + soup.find_all('h1')
        for tag in tags:
            content = str(tag.string).strip()
            if content:
                text.append(content)

        text = [_.split('|')[0].split(' -')[0].split(' —')[0] for _ in text]
        text = [_ for _ in text if len(_.split()) > 1]
        text = list(set(text))

        return "\n".join(text)
    except:
        return ''
