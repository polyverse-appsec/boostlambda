import tiktoken
import os


class OpenAIDefaults:
    boost_max_tokens_default = 0  # 0 is disabled max, 32768 for gpt-4-32k, 4000 for gpt3.5 and 8192 for gpt4
    boost_tuned_max_tokens = boost_max_tokens_default  # could be 1000 based on OpenAI recommendation, no obvious response time difference

    # Models to choose from
    boost_model_gpt4 = "gpt-4"              # best overall model
    boost_model_gpt4_32k = "gpt-4-32k"          # best overall model with 32k limit
    boost_model_gpt35_cheap_chat = "gpt-3.5-turbo"   # 1/10 cost of Davinci-3, and faster than gpt4, but less effective (no codex)
    boost_model_gpt35_generic = "text-davinci-003"   # more expensive 3x model, but faster than gpt4
    boost_model_cheap_fast_generic = "ada"  # cheapest and fastest, least accurate circa 2019
    boost_model_codex = "code-davinci-002"

    # default model from above choices
    boost_default_gpt_model = boost_model_gpt4

    # tokenizer encodings
    encoding_gpt = "cl100k_base"  # used for gpt4
    encoding_codex = "p50k_base"  # used for codex/davinci

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


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    if (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt4):
        if (code_encoding is None):
            return len(string)

        num_tokens = len(code_encoding.encode(string))
        return num_tokens

    # else we assume we are using gpt3.5 or older
    if (text_encoding is None):
        return len(string)

    num_tokens = len(text_encoding.encode(string))
    return num_tokens


def get_openai_usage(payload, input: bool = True):

    token_count = num_tokens_from_string(payload)

    if (OpenAIDefaults.boost_default_gpt_model == OpenAIDefaults.boost_model_gpt4):
        if (input):
            if (token_count < 8000):
                cost_per_token = cost_gpt4_per_prompt_token_lt_8000
            else:
                cost_per_token = cost_gpt4_per_prompt_token_lt_32000
        else:
            if (token_count < 8000):
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

    total_cost = token_count * cost_per_token

    return token_count, total_cost


def get_boost_cost(payloadLength):
    return (payloadLength / 1024) * boost_cost_per_kb
