import tiktoken
import os
import json
from typing import Tuple, List


class OpenAIDefaults:
    boost_max_tokens_unlimited = 0

    # 128k tokens
    boost_max_tokens_gpt_4_turbo = 128000
    boost_max_tokens_gpt_4_turbo_output = 4096

    boost_max_tokens_gpt_4 = 8192
    boost_max_tokens_gpt_4_32k = 32768

    boost_max_tokens_gpt_35 = 4096

    boost_max_tokens_default = boost_max_tokens_gpt_4  # 0 is disabled max, 32768 for gpt-4-32k, 4000 for gpt3.5 and 8192 for gpt4

    rate_limit_tokens_per_minute = 40000  # 40k tokens per minute

    boost_tuned_max_tokens = boost_max_tokens_default  # could be 1000 based on OpenAI recommendation, no obvious response time difference

    # Models to choose from
    boost_model_gpt4_turbo = "gpt-4-turbo-preview"   # latest model as of November 2023 (trained to April 2023)
    boost_model_gpt4 = "gpt-4"                      # best overall model
    boost_model_gpt4_current = "gpt-4-0613"         # best overall model - date specific, expires
    boost_model_gpt4_32k = "gpt-4-32k"              # best overall model with 32k limit
    boost_model_gpt35_cheap_chat = "gpt-3.5-turbo"  # 1/10 cost of Davinci-3, and faster than gpt4, but less effective (no codex)
    boost_model_gpt35_generic = "text-davinci-003"  # more expensive 3x model, but faster than gpt4
    boost_model_cheap_fast_generic = "ada"          # cheapest and fastest, least accurate circa 2019
    boost_model_codex = "code-davinci-002"

    # default model from above choices
    boost_default_gpt_model = boost_model_gpt4

    # tokenizer encodings
    encoding_gpt4_and_gpt35 = "cl100k_base"  # used for gpt4, 3.5 turbo
    encoding_codex = "p50k_base"  # used for codex/davinci
    encoding_gpt3 = "gpt2"  # used for gpt3

    # temperature settings
    temperature_terse_and_accurate = 0.1
    temperature_medium_with_explanation = 0.5
    temperature_verbose_and_explanatory = 1.0

    default_temperature = temperature_verbose_and_explanatory


if 'AWS_CHALICE_CLI_MODE' not in os.environ and 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:

    print("OpenAIDefaults.boost_default_gpt_model: " + OpenAIDefaults.boost_default_gpt_model)


def max_tokens_for_model(model: str):
    if OpenAIDefaults.boost_tuned_max_tokens == 0:
        return OpenAIDefaults.boost_max_tokens_unlimited

    # if the data has a max tokens set, use that
    if model is None:
        # use the default
        return OpenAIDefaults.boost_max_tokens_default

    if OpenAIDefaults.boost_model_gpt4_32k in model:
        return OpenAIDefaults.boost_max_tokens_gpt_4_32k
    elif OpenAIDefaults.boost_model_gpt4_turbo in model:
        return OpenAIDefaults.boost_max_tokens_gpt_4_turbo
    elif OpenAIDefaults.boost_model_gpt4 in model:
        return OpenAIDefaults.boost_max_tokens_gpt_4
    elif OpenAIDefaults.boost_model_gpt35_cheap_chat in model:
        return OpenAIDefaults.boost_max_tokens_gpt_35

    else:
        return OpenAIDefaults.boost_max_tokens_default

# https://openai.com/pricing
# | Context size | Cost per 1K tokens  | Cost per 1K tokens        |
# | Model        | Prompt              | Completion                |
# |--------------|---------------------|---------------------------|
# | 8K context   | $0.03 / 1K tokens   | $0.06 / 1K tokens         |
# | 32K context  | $0.06 / 1K tokens   | $0.12 / 1K tokens         |
# | 128k context | $0.01 / 1K tokens   | $0.03 / 1K tokens         |


boost_base_monthly_cost = 10.0

# Assuming the cost per kb is 0.06 cents
boost_cost_per_kb = 0.06

# input vs output costs for GPT4 Turbo
cost_gpt4_turbo_per_token_input = 0.01 / 1000
cost_gpt4_turbo_per_token_output = 0.03 / 1000

# Assuming the cost per token is 0.03 cents (up to 8k tokens or double price for 32k tokens)
cost_gpt4_per_prompt_token_lt_8000 = 0.03 / 1000
cost_gpt4_per_prompt_token_lt_32000 = 0.06 / 1000

cost_gpt4_per_completion_token_lt_8000 = 0.06 / 1000
cost_gpt4_per_completion_token_lt_32000 = 0.12 / 1000

cost_gpt35_per_token = 0.002 / 1000

cost_codex_per_token = 0.02 / 1000

cost_codex_cheap_per_token = 0.0004 / 1000

encoding_calculated_variation_buffer_gpt35 = 1.04  # 4% buffer for variation in encoding size
encoding_calculated_variation_buffer_gpt4 = 1.025  # 2.5% buffer for variation in encoding size

text_encoding = None
code_encoding = None
original_encoding = None
encoding_loaded = False


def load_encodings():
    global text_encoding
    global code_encoding
    global original_encoding
    global encoding_loaded

    if encoding_loaded:
        return

    encoding_loaded = True

    try:
        text_encoding = tiktoken.get_encoding(OpenAIDefaults.encoding_gpt4_and_gpt35)
        code_encoding = tiktoken.get_encoding(OpenAIDefaults.encoding_codex)
        original_encoding = tiktoken.get_encoding(OpenAIDefaults.encoding_gpt3)
    except Exception as error:
        text_encoding = None
        code_encoding = None
        original_encoding = None
        print("Failed to load OpenAI encodings due to error: " + str(error))
        pass

    # Don't run this under Chalice deployment
    if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
        print("Loaded OpenAI encodings")


# Returns the number of tokens in a text string, and the encoded string
def num_tokens_from_string(string: str, model=OpenAIDefaults.boost_default_gpt_model) -> Tuple[int, List[int]]:
    load_encodings()

    tokenized = None
    encoding_calculated_variation_buffer = None

    # Determine the encoding and buffer based on the model
    if model in [OpenAIDefaults.boost_model_cheap_fast_generic]:
        if original_encoding is None:
            raise Exception("No original encoding available")
        tokenized = original_encoding.encode(string)
        encoding_calculated_variation_buffer = encoding_calculated_variation_buffer_gpt35
    elif model in [OpenAIDefaults.boost_model_codex, OpenAIDefaults.boost_model_gpt35_generic]:
        if code_encoding is None:
            raise Exception("No code encoding available")
        tokenized = code_encoding.encode(string)
        encoding_calculated_variation_buffer = encoding_calculated_variation_buffer_gpt35
    else:
        if model not in [
                OpenAIDefaults.boost_model_gpt4_turbo,
                OpenAIDefaults.boost_model_gpt4,
                OpenAIDefaults.boost_model_gpt4_current,
                OpenAIDefaults.boost_model_gpt35_cheap_chat,
                OpenAIDefaults.boost_model_gpt35_generic,
                OpenAIDefaults.boost_model_gpt4_32k]:
            print(f"Using default Token Encoding due to known model: {model}")

        # else we assume we are using gpt3.5 or newer

        if text_encoding is None:
            raise Exception("No text encoding available")
        tokenized = text_encoding.encode(string)
        encoding_calculated_variation_buffer = encoding_calculated_variation_buffer_gpt4

    num_tokens = len(tokenized)

    # to accomodate OpenAI engine variation in encoding - we'll add 2.5%
    num_tokens = round(encoding_calculated_variation_buffer * float(num_tokens))

    return num_tokens, tokenized


# Returns the decoded string from an array of tokens based on a specific model
def decode_string_from_input(input: list[int], model=OpenAIDefaults.boost_default_gpt_model) -> str:
    load_encodings()

    if model in [OpenAIDefaults.boost_model_cheap_fast_generic]:
        if (original_encoding is None):
            raise Exception("No original encoding available")

        # encoding and decoding are not working yet for old <= 3.0 models
        raise Exception("Encoding and decoding are not working yet for old <= 3.0 models")

        output = original_encoding.decode(input)
        return output

    # code focused models
    elif model in [
            OpenAIDefaults.boost_model_codex,
            OpenAIDefaults.boost_model_gpt35_generic]:
        if code_encoding is None:
            raise Exception("No code encoding available")

        output = code_encoding.decode(input)
        return output

    if model not in [
            OpenAIDefaults.boost_model_gpt4_turbo,
            OpenAIDefaults.boost_model_gpt4,
            OpenAIDefaults.boost_model_gpt4_current,
            OpenAIDefaults.boost_model_gpt35_cheap_chat,
            OpenAIDefaults.boost_model_gpt35_generic,
            OpenAIDefaults.boost_model_gpt4_32k]:
        print(f"Using default Token Encoding due to known model: {model}")

    # else we assume we are using gpt3.5 or newer
    if text_encoding is None:
        raise Exception("No text encoding available")

    output = text_encoding.decode(input)
    return output


def get_openai_usage_per_string(payload: str, input: bool, model=OpenAIDefaults.boost_default_gpt_model) -> Tuple[int, float]:
    token_count, _ = num_tokens_from_string(payload, model)

    return get_openai_usage_per_token(token_count, input, model)


def get_openai_usage_per_token(num_tokens: int, input: bool, model=OpenAIDefaults.boost_default_gpt_model) -> Tuple[int, float]:

    if model in [OpenAIDefaults.boost_model_gpt4, OpenAIDefaults.boost_model_gpt4_32k, OpenAIDefaults.boost_model_gpt4_current]:
        if (input):
            if (num_tokens < OpenAIDefaults.boost_max_tokens_gpt_4):
                cost_per_token = cost_gpt4_per_prompt_token_lt_8000
            else:
                cost_per_token = cost_gpt4_per_prompt_token_lt_32000
        else:
            if (num_tokens < OpenAIDefaults.boost_max_tokens_gpt_4):
                cost_per_token = cost_gpt4_per_completion_token_lt_8000
            else:
                cost_per_token = cost_gpt4_per_completion_token_lt_32000

    elif model == OpenAIDefaults.boost_max_tokens_gpt_4_turbo:
        if (input):
            cost_per_token = cost_gpt4_turbo_per_token_input
        else:
            cost_per_token = cost_gpt4_turbo_per_token_output

    elif model == OpenAIDefaults.boost_model_gpt35_generic:
        cost_per_token = cost_codex_per_token
    elif model == OpenAIDefaults.boost_model_gpt35_cheap_chat:
        cost_per_token = cost_gpt35_per_token
    elif model == OpenAIDefaults.boost_model_cheap_fast_generic:
        cost_per_token = cost_codex_cheap_per_token
    else:
        cost_per_token = cost_codex_per_token

    total_cost = num_tokens * cost_per_token

    return num_tokens, total_cost


def get_boost_cost(payloadLength):
    return (payloadLength / 1024) * boost_cost_per_kb


# This doesn't appear to be highly accurate way to measure function token usage
# it tends to overestimate the cost of functions - by at least 25-50%
def tokens_from_function(params, model) -> int:
    use_aggressive_function_token_measure = True

    function_content_size = 0
    for key in (['functions'] if use_aggressive_function_token_measure else ['functions', 'function_call']):
        if key in params:
            if not use_aggressive_function_token_measure:
                function_content_size += num_tokens_from_string(json.dumps(params[key]), model)[0]
            else:
                for function in params[key]:
                    # note that the function-related params are stored as dictionaries, unlike other user content
                    for func_param in function['parameters']:
                        function_content_size += num_tokens_from_string(json.dumps(function['parameters'][func_param]), model)[0]
                    function_content_size += num_tokens_from_string(json.dumps(function['name']), model)[0]

    return function_content_size
