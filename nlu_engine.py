import re
from transformers import LlamaForCausalLM, LlamaTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType, PeftConfig, PeftModel
import numpy as np
import os

from context_service import get_context

import logging

# Define logger
logger = logging.getLogger('BOT')


MAX_PROMPT_LEN=150
MAX_SAMPLE=3
MAX_LEN_APPEND=100
MAX_CONTEXT_LEN=5


logger.info('Load main NLU model...')
generator_tokenizer = LlamaTokenizer.from_pretrained("huggyllama/llama-7b")
generator_tokenizer.pad_token_id = 0

if os.environ.get('DEBUG'):
    generate_model = None
else:
    generate_model = LlamaForCausalLM.from_pretrained('/app/models/generator_llama')
    generate_model = PeftModel.from_pretrained(generate_model, "/app/models/train_llama_lora/")


score_pattern_tokens = generator_tokenizer("Хорошо", return_tensors="pt")['input_ids'][0][1:]
logger.info('Ready to work!')


def truncate_text_to_max(text, max_len):
    words = text.split()
    if len(words) > max_len:
        return ' '.join(words[:max_len])
    else:
        return text


def generate_message(contexts, message, progress_cb=None, temperature=0.1):
    if not generate_model:
        return "test output\nHistory:\n" + "\n".join(contexts) + "\nsource message:\n" + message, 1.0

    message = truncate_text_to_max(message, MAX_PROMPT_LEN)
    if contexts and len(contexts) > MAX_CONTEXT_LEN:
        contexts = [contexts[0]] + contexts[-(MAX_CONTEXT_LEN-1):]

    message = re.sub(r'\s+', ' ', message).strip()
    context = " ".join(contexts) if contexts else ''

    chat_prompt = ''
    for c in contexts:
        chat_prompt += "Comment:" + c + "\n\n"
    chat_prompt = chat_prompt.strip()

    if context:
        prompt_contexts = get_context(context, 1)
        logger.info('Generate reply to: ' + message + '; with context: ' + context)
    else:
        prompt_contexts = get_context(message, 1)
        logger.info('Generate reply to: ' + message)

    # generate context and scores it
    pre_scores = []
    for prompt_context in [None] + prompt_contexts:
        prompt = ""
        if prompt_context:
            prompt_context = truncate_text_to_max(prompt_context, MAX_PROMPT_LEN)
            prompt = "Comment:" + prompt_context + "\n\n"

        if chat_prompt:
            prompt += chat_prompt

        prompt = prompt.strip()
        prompt += "\n\nComment:" + message
        prompt = prompt.strip()

        main_inputs = generator_tokenizer(prompt + "\n\nWrite comment:", return_tensors="pt")
        main_score_generate = generate_model.generate(
            input_ids=main_inputs["input_ids"],
            max_new_tokens=MAX_LEN_APPEND,
            pad_token_id=generator_tokenizer.pad_token_id,
            do_sample=False,
            output_scores=True, return_dict_in_generate=True
        )

        pre_scores.append((np.mean([_.std() for _ in main_score_generate.scores]), prompt, main_inputs))
        if progress_cb:
            progress_cb(1, 1)

    pre_scores = sorted(pre_scores, key=lambda score_prompt: -score_prompt[0])
    prompt_score, main_prompt, main_inputs = pre_scores[0]

    logger.info('Calc prompt: ' + main_prompt)
    logger.info(f'Prompt score: {prompt_score}')

    # generate answers and score it
    generate_ids = generate_model.generate(
        input_ids=main_inputs["input_ids"],
        max_new_tokens=MAX_LEN_APPEND,
        pad_token_id=generator_tokenizer.pad_token_id,
        num_return_sequences=MAX_SAMPLE,
        do_sample=True,
        temperature=temperature,
        top_p=1000,
        repetition_penalty=1.1,
        renormalize_logits=True,
        num_beams=2,
    )
    if progress_cb:
        progress_cb(1, 1)

    output_variants = []
    output_comments = {}
    for i in range(MAX_SAMPLE):
        output_tokens = generate_ids[i][main_inputs['input_ids'][0].shape[0]:]
        output_comment = generator_tokenizer.decode(output_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        if output_comment in output_comments:
            continue
        output_comments[output_comment] = 1

        prompt = main_prompt + f"\n\nComment:{output_comment}\n\nComment:Оцени ответ: Хорошо или Плохо\n\nWrite comment:"
        inputs = generator_tokenizer(prompt, return_tensors="pt")

        score_outputs = generate_model.generate(input_ids=inputs["input_ids"], max_new_tokens=10, output_scores=True,
                                       return_dict_in_generate=True)
        score_outputs = score_outputs.scores
        score_probs = [sc[0].softmax(dim=-1) for sc in score_outputs]
        pattern_probs = []
        for score_pattern_token_id in score_pattern_tokens:
            for j in range(score_pattern_tokens.shape[0]):
                pattern_probs.append(
                    score_probs[j][score_pattern_token_id]
                )
        max_score_prob = np.max(pattern_probs)

        output_variants.append((max_score_prob, output_comment))
        if progress_cb:
            progress_cb(1, 1)

    output_variants = sorted(output_variants, key=lambda score_comment: -score_comment[0])
    max_score, output_comment = output_variants[0]
    return output_comment, max_score


def generate_answer_for_chat(contexts: list, message: str, progress_cb=None):
    return generate_message(contexts, message, progress_cb)


def generate_comment_to_post(post, temperature=0.1):
    return generate_message([], post + "\nНапиши комментарий к новости", None, temperature)
