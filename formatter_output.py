import re


def process_reply(text):
    formatted_output = re.sub(r'#query:[^\n]+', '', text)
    formatted_output = re.sub(r'#[^\s]+', '', formatted_output)
    formatted_output = re.sub(r'🇷🇺.+', '', formatted_output)
    formatted_output = re.sub(r'(— [А-ЯЁ])', "\n\\1", formatted_output, flags=re.UNICODE)
    formatted_output = re.sub('<s>', ' ', formatted_output)

    return formatted_output


def preprocess_messages(text):
    text = re.sub(r'#[^\s]+', '', text)
    text = re.sub(r'@[^\s]+', '', text)

    return text
