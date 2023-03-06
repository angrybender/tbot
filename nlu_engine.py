from transformers import GPT2Tokenizer, GPT2LMHeadModel
import torch
from transformers import AutoTokenizer, AutoModel
import re
import numpy as np
import keras

import logging
from sys import stdout

# Define logger
logger = logging.getLogger('BOT')


MAX_LEN=100
MAX_LEN_APPEND=200
MAX_GENERATE_SEQ=2
MAX_ATTEMTS=10
MAX_EPOHS=1
EPOHS_WINDOW=5
EARLY_STEP_TRESHOLD=0.8
EPOCH_TRESHOLD=0.1


logger.info('Load main NLU model...')
generator_tokenizer = GPT2Tokenizer.from_pretrained('/app/models/main/tokenizer')
generator_tokenizer.add_special_tokens({'pad_token': '<pad>', 'bos_token': '<s>', 'eos_token': '</s>'})

generate_model = GPT2LMHeadModel.from_pretrained('/app/models/main/generator')

logger.info('Load range model...')
range_model = keras.models.load_model('/app/models/range_model')


class BertText:
    D_SIZE = 312

    def __init__(self):
        self._tokenizer = AutoTokenizer.from_pretrained("/app/models/embeddings_models/tokenizer")
        self._model = AutoModel.from_pretrained("/app/models/embeddings_models")

    def _embed_bert_cls(self, text):
        t = self._tokenizer(text, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            model_output = self._model(**{k: v.to(self._model.device) for k, v in t.items()})
        embeddings = model_output.last_hidden_state[:, 0, :]
        embeddings = torch.nn.functional.normalize(embeddings)
        return embeddings[0].cpu().numpy()

    def fit_transform(self, texts, use_progress=True):
        X = []
        for t in texts:
            X.append(self._embed_bert_cls(t))
        return X


range_vectorizer = BertText()
logger.info('Ready to work!')


def generate_message(context, message, progress_cb=None):
    message = re.sub(r'\s+', ' ', message).strip()
    source_message = message
    context = re.sub(r'\s+', ' ', context).strip()

    all_outputs = []
    max_score = 0.0

    if context:
        logger.info('Generate reply to: ' + message + '; with context: ' + context)
    else:
        logger.info('Generate reply to: ' + message)

    for j in range(MAX_EPOHS):
        logger.info("Epoch: " + str(j + 1))

        if j == 0:
            message_input = "<s>#context: " + context + "\n#query: " + message + "\n"
        else:
            message_input = message

        range_input_vector = range_vectorizer.fit_transform([context + " " + message], False)
        input_ids = generator_tokenizer.encode(message_input, return_tensors="pt")

        generated_texts = []
        max_new_tokens = MAX_LEN if j == 0 else MAX_LEN_APPEND
        for i in range(MAX_ATTEMTS):
            if progress_cb:
                progress_cb(j, i)

            out = generate_model.generate(
                input_ids, max_new_tokens=max_new_tokens, pad_token_id=generator_tokenizer.pad_token_id,
                num_return_sequences=MAX_GENERATE_SEQ, do_sample=True,
                temperature=0.75, top_p=1.,
                repetition_penalty=1.1,
                renormalize_logits=True,
            )

            for out_v in out:
                out_v = out_v[input_ids.shape[1]:]

                msg = generator_tokenizer.decode(out_v)
                msg = msg.replace('<pad>', '').split('</s>')[0]

                msg = msg.split('#answer:')[-1].strip()

                range_ouput_vector = range_vectorizer.fit_transform([msg], False)
                range_score = range_model.predict([np.array(range_input_vector), np.array(range_ouput_vector)])[0][0]

                generated_texts.append((msg, range_score))

            generated_texts = [msg_score for msg_score in generated_texts if msg_score[0].find("\n\n") == -1]
            generated_texts = sorted(generated_texts, key=lambda t_s: -t_s[1])
            if len(generated_texts) == 0:
                generated_texts = [('', 0.0)]

            logger.info("    Step: " + str(i + 1) + ", max score=" + str(generated_texts[0][1]))

            if generated_texts[0][1] >= EARLY_STEP_TRESHOLD:
                break

        msg, score = generated_texts[0]
        max_score = max(max_score, score)
        if j > 0:
            sentences = msg.split('. ')
            if len(sentences) > 1:
                msg = '. '.join(sentences[:-1]) + '.'

        all_outputs.append(msg)
#        print("    epoch message=", msg, "score=", score)
        if score < EPOCH_TRESHOLD:
            break

        message = source_message + " " + " ".join(all_outputs[-EPOHS_WINDOW:])

    return " ".join(all_outputs), max_score
