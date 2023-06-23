import tiktoken
import os
from typing import Tuple, List


class OpenAIDefaults:
    boost_max_tokens_unlimited = 0
    boost_max_tokens_gpt_4 = 8192
    boost_max_tokens_gpt_4_32k = 32768
    boost_max_tokens_gpt_35 = 4096

    boost_max_tokens_default = boost_max_tokens_gpt_4  # 0 is disabled max, 32768 for gpt-4-32k, 4000 for gpt3.5 and 8192 for gpt4

    boost_tuned_max_tokens = boost_max_tokens_default  # could be 1000 based on OpenAI recommendation, no obvious response time difference

    # Models to choose from
    boost_model_gpt4 = "gpt-4"                      # best overall model
    boost_model_gpt4_current = "gpt-4-0613"         # best overall model - date specific, expires
    boost_model_gpt4_32k = "gpt-4-32k"              # best overall model with 32k limit
    boost_model_gpt35_cheap_chat = "gpt-3.5-turbo"  # 1/10 cost of Davinci-3, and faster than gpt4, but less effective (no codex)
    boost_model_gpt35_generic = "text-davinci-003"  # more expensive 3x model, but faster than gpt4
    boost_model_cheap_fast_generic = "ada"          # cheapest and fastest, least accurate circa 2019
    boost_model_codex = "code-davinci-002"

    # default model from above choices
    boost_default_gpt_model = boost_model_gpt4_current

    # tokenizer encodings
    encoding_gpt = "cl100k_base"  # used for gpt4
    encoding_codex = "p50k_base"  # used for codex/davinci

    # temperature settings
    temperature_terse_and_accurate = 0.1
    temperature_medium_with_explanation = 0.5
    temperature_verbose_and_explanatory = 1.0

    default_temperature = temperature_verbose_and_explanatory


def max_tokens_for_model(model: str):
    if OpenAIDefaults.boost_tuned_max_tokens == 0:
        return OpenAIDefaults.boost_max_tokens_unlimited

    # if the data has a max tokens set, use that
    if model is None:
        # use the default
        return OpenAIDefaults.boost_max_tokens_default

    if OpenAIDefaults.boost_model_gpt4_32k in model:
        return OpenAIDefaults.boost_max_tokens_gpt_4_32k
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


# Assuming the cost per kb is 0.06 cents
boost_cost_per_kb = 0.06

# Assuming the cost per token is 0.01 cents
cost_gpt4_per_prompt_token_lt_8000 = 0.03 / 1000
cost_gpt4_per_prompt_token_lt_32000 = 0.06 / 1000

cost_gpt4_per_completion_token_lt_8000 = 0.06 / 1000
cost_gpt4_per_completion_token_lt_32000 = 0.12 / 1000

cost_gpt35_per_token = 0.002 / 1000

cost_codex_per_token = 0.02 / 1000

cost_codex_cheap_per_token = 0.0004 / 1000

try:
    text_encoding = tiktoken.get_encoding(OpenAIDefaults.encoding_gpt)
    code_encoding = tiktoken.get_encoding(OpenAIDefaults.encoding_codex)
except Exception as error:
    text_encoding = None
    code_encoding = None
    print("Failed to load OpenAI encodings due to error: " + str(error))
    pass

# Don't run this under Chalice deployment
if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    print("Loaded OpenAI encodings")


def num_tokens_from_string(string: str) -> Tuple[int, List[int]]:
    # Returns the number of tokens in a text string, and the encoded string
    if (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt4):
        if (code_encoding is None):
            raise Exception("No encoding available")

        tokenized = code_encoding.encode(string)
        num_tokens = len(tokenized)
        return num_tokens, tokenized

    # else we assume we are using gpt3.5 or older
    if (text_encoding is None):
        raise Exception("No encoding available")

    tokenized = text_encoding.encode(string)
    num_tokens = len(tokenized)
    return num_tokens, tokenized


def decode_string_from_input(input: list[int]) -> str:
    # Returns the number of tokens in a text string, and the encoded string
    if (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt4):
        if (code_encoding is None):
            raise Exception("No encoding available")

        output = code_encoding.decode(input)
        return output

    # else we assume we are using gpt3.5 or older
    if (text_encoding is None):
        raise Exception("No encoding available")

    output = text_encoding.decode(input)
    return output


def get_openai_usage_per_string(payload: str, input: bool) -> Tuple[int, float]:
    token_count, _ = num_tokens_from_string(payload)
    return get_openai_usage_per_token(token_count, input)


def get_openai_usage_per_token(num_tokens: int, input: bool) -> Tuple[int, float]:

    if (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt4):
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
    elif (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt35_generic):
        cost_per_token = cost_codex_per_token
    elif (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt35_cheap_chat):
        cost_per_token = cost_gpt35_per_token
    elif (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_cheap_fast_generic):
        cost_per_token = cost_codex_cheap_per_token
    else:
        cost_per_token = cost_codex_per_token

    total_cost = num_tokens * cost_per_token

    return num_tokens, total_cost


def get_boost_cost(payloadLength):
    return (payloadLength / 1024) * boost_cost_per_kb
