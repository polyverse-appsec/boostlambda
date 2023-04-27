import tiktoken
import os


class OpenAIDefaults:
    boost_max_tokens_default = 4000
    boost_default_gpt_model = "gpt-4"
    boost_codex_model = "code-davinci-002"
    boost_tuned_max_tokens = 4000  # could be 1000 based on OpenAI recommendation, no obvious response time difference
    encoding_gpt = "cl100k_base"  # used for gpt4
    encoding_codex = "p50k_base"  # used for codex/davinci

# https://openai.com/pricing
# | Context size | Cost per 1K tokens  | Cost per 1K tokens        |
# | Model        | Prompt              | Completion                |
# |--------------|---------------------|---------------------------|
# | 8K context   | $0.03 / 1K tokens   | $0.06 / 1K tokens         |
# | 32K context  | $0.06 / 1K tokens   | $0.12 / 1K tokens         |


# Assuming the cost per kb is 0.03 cents
cost_per_kb = 0.03

# Assuming the cost per token is 0.01 cents
cost_per_prompt_token_lt_8000 = 0.03 / 1000
cost_per_prompt_token_lt_32000 = 0.06 / 1000

cost_per_completion_token_lt_8000 = 0.06 / 1000
cost_per_completion_token_lt_32000 = 0.12 / 1000


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
    if (text_encoding is None):
        return len(string)

    num_tokens = len(text_encoding.encode(string))
    return num_tokens


def get_openai_usage(payload, input: bool = True):

    token_count = num_tokens_from_string(payload)

    if (input):
        if (token_count < 8000):
            cost_per_token = cost_per_prompt_token_lt_8000
        else:
            cost_per_token = cost_per_prompt_token_lt_32000
    else:
        if (token_count < 8000):
            cost_per_token = cost_per_completion_token_lt_8000
        else:
            cost_per_token = cost_per_completion_token_lt_32000

    total_cost = token_count * cost_per_token

    return token_count, total_cost


def get_boost_cost(payloadLength):
    return (payloadLength / 1024) * cost_per_kb
