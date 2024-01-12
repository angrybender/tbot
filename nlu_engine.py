import re
import os
import requests

from context_service import get_context

import logging

# Define logger
logger = logging.getLogger('BOT')

MAX_PROMPT_LEN=150
MAX_SAMPLE=3
MAX_LEN_APPEND=100
MAX_CONTEXT_LEN=5
DEFAULT_TEMPERATURE=0.1
NLU_API_HOST = os.environ.get('NLU_API_HOST')
NLU_API_TOKEN = os.environ.get('NLU_API_TOKEN')


def truncate_text_to_max(text, max_len):
    words = text.split()
    if len(words) > max_len:
        return ' '.join(words[:max_len])
    else:
        return text


def generate_message(contexts, message, temperature=0.1):
    message = truncate_text_to_max(message, MAX_PROMPT_LEN)
    if contexts and len(contexts) > MAX_CONTEXT_LEN:
        contexts = [contexts[0]] + contexts[-(MAX_CONTEXT_LEN-1):]

    message = re.sub(r'\s+', ' ', message).strip()
    context = " ".join(contexts) if contexts else ''

    if context:
        prompt_contexts = get_context(context, 1)
        logger.info('Generate reply to: ' + message + '; with context: ' + context)
    else:
        prompt_contexts = get_context(message, 1)
        logger.info('Generate reply to: ' + message)

    generate_parameters = {
        'prompt_extended_contexts': prompt_contexts,
        'context': contexts,
        'message': message,
        'temperature': temperature,
        'token': NLU_API_TOKEN,
    }

    try:
        output = requests.post(NLU_API_HOST, json=generate_parameters).json()
    except Exception as e:
        raise Exception(f"NLU REST API error: {e}")

    check_duplicated = output['output'].lower().replace(message.lower(), '')
    if len(check_duplicated) < 0.25*len(output['output']):
        output['score'] = 0.0

    sub_tokens = output['output'].lower().split(',')
    if len(sub_tokens) > 5:
        check_duplicated = output['output'].lower().replace(sub_tokens[0].lower() + ',', '').strip()

        if len(check_duplicated) < 0.25 * len(output['output']):
            output['score'] = 0.0

    return output['output'], output['score']


def generate_answer_for_chat(contexts: list, message: str):
    return generate_message(contexts, message, DEFAULT_TEMPERATURE)


def generate_comment_to_post(post, temperature=0.1):
    return generate_message([], post + "\nНапиши комментарий к новости", temperature)
