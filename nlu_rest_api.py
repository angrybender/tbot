from flask import Flask, request, jsonify
from llm_service import generate_by_context_and_message
import os
import logging
from sys import stdout

# Define logger
logger = logging.getLogger('BOT')
logger.setLevel(logging.INFO)
logFormatter = logging.Formatter("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

app = Flask(__name__)
AUTH_TOKEN = os.environ.get('NLU_API_TOKEN')


@app.route("/generate", methods=['POST'])
def post_generate():
    data = request.json

    token = data.get('token')
    if token != AUTH_TOKEN:
        return 'error', 401

    prompt_extended_contexts = data.get('prompt_extended_contexts')
    context = data.get('context')
    message = data.get('message')
    temperature = data.get('temperature')

    output, score = generate_by_context_and_message(
        prompt_extended_contexts,
        context,
        message,
        temperature
    )

    return jsonify({
        'output': output,
        'score': score
    })

