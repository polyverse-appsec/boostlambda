# generic.py
import openai
import traceback
from .. import pvsecret
import os
import math
from typing import List, Tuple

from markdown import markdown_emphasize

from chalicelib.telemetry import capture_metric, InfoMetrics, CostMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults, num_tokens_from_string, decode_string_from_input
from chalicelib.payments import update_usage_for_text

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key


class GenericProcessor:

    def __init__(self, api_version, prompt_filenames):
        self.api_version = api_version
        self.prompt_filenames = prompt_filenames
        print(f"{self.__class__.__name__}_api_version: ", self.api_version)
        self.prompts = self.load_prompts()

    def load_prompts(self):
        promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
        prompts = {}

        for prompt_name, filename in self.prompt_filenames.items():
            with open(os.path.join(promptdir, filename), 'r') as f:
                prompts[prompt_name] = f.read()

        return prompts

    def generate_messages(self, data, prompt_format_args):

        prompt = self.prompts['main'].format(**prompt_format_args)
        role_system = self.prompts['role_system']

        this_messages = [
            {
                "role": "system",
                "content": role_system
            },
            {
                "role": "user",
                "content": prompt
            }]

        return this_messages, prompt

    def calculate_chunk_size(self, input_tokens, buffer_size) -> int:
        n_chunks = math.ceil(input_tokens / buffer_size)
        chunk_size = math.ceil(input_tokens / n_chunks)
        return chunk_size

    def chunk_input_based_on_token_limit(self, prompt, input_token_buffer, input_tokens) -> Tuple[List[str], int]:
        chunk_size = self.calculate_chunk_size(input_tokens, input_token_buffer)
        _, tokens = num_tokens_from_string(prompt)

        chunks = []
        for i in range(0, len(tokens), chunk_size):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = decode_string_from_input(chunk_tokens)
            chunks.append(chunk_text)

        return chunks, input_token_buffer - chunk_size

    def reprocess_inputs_against_token_limit(self, params, prompt, function_name, tuned_max_tokens, total_max, input_tokens) -> Tuple[bool, str, int]:
        # if we're doing 'summarize', we'll leave most buffer for the input, and a small amount for the output - fixed
        # if we're doing any other input, we'll roughly split the token buffer into 50/50 for input and output

        if function_name == 'summarize':
            # we'll leave 90% of the buffer for the input, and 10% for the output
            input_token_buffer = math.floor(total_max * 0.9)
        else:
            input_token_buffer = math.floor(total_max * 0.5)

        # If we are over the token limit, we need to reprocess the input
        remaining_input_buffer = input_token_buffer - input_tokens
        if remaining_input_buffer < 0:
            # If we are over the token limit, we're going to need to truncate the original input by enough to create
            # enough buffer to get a useful result - say 20% - 50% of the original input
            prompts, max_chunk_size = self.chunk_input_based_on_token_limit(prompt, input_token_buffer, input_tokens)

            # update output max tokens to be the remaining buffer after the max chunk size
            tuned_max_tokens = tuned_max_tokens - max_chunk_size

            # we may be discarding / truncating the rest of the input, but we'll retain the first chunk for processing
            prompt = prompts[0]

            truncated = True
        else:
            # since we have remaining input buffer, use it for the output buffer
            tuned_max_tokens = tuned_max_tokens - input_tokens
            truncated = False

        return truncated, prompt, tuned_max_tokens

    def update_messages(self, this_messages, prompt) -> any:

        # Replace the 'user' 'content' with the new prompt
        for message in this_messages:
            if message['role'] == 'user':
                message['content'] = prompt   # Replace with new prompt

        return this_messages

    def process_input(self, data, account, function_name, correlation_id, prompt_format_args) -> dict:
        # enable user to override the model to gpt-3 or gpt-4
        model = OpenAIDefaults.boost_default_gpt_model
        if 'model' in data:
            model = data['model']

        # And then in process_input
        this_messages, prompt = self.generate_messages(data, prompt_format_args)

        params = {
            "model": model,
            "messages": this_messages}

        # https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
        if 'top_p' in data:
            params["top_p"] = float(data['top_p'])
        elif 'temperature' in data:
            params["temperature"] = float(data['temperature'])

        # Get the cost of the inputs - so we have can manage our token limits
        prompt_size = len(str(this_messages))
        user_input = self.collate_all_user_input(data)
        user_input_size = len(user_input)
        openai_input_tokens, openai_input_cost = get_openai_usage(str(this_messages))
        openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(user_input)

        truncated = False
        chunked = False
        if OpenAIDefaults.boost_tuned_max_tokens != 0:
            # subtract our constructed input from our total token limit and set that as max tokens
            this_boost_tuned_max_tokens = OpenAIDefaults.boost_tuned_max_tokens - openai_input_tokens
            chunked = True

            truncated, prompt, this_boost_tuned_max_tokens = self.reprocess_inputs_against_token_limit(
                params, prompt, function_name, this_boost_tuned_max_tokens, OpenAIDefaults.boost_tuned_max_tokens, openai_input_tokens)

            if truncated:
                print(f"{function_name}:Truncation:{account['email']}:{correlation_id}:Truncated user input, discarded {OpenAIDefaults.boost_tuned_max_tokens - this_boost_tuned_max_tokens} tokens")
                params['messages'] = self.update_messages(params['messages'], prompt)

            params["max_tokens"] = this_boost_tuned_max_tokens

        try:
            response = openai.ChatCompletion.create(**params)
        except Exception as e:
            # check exception type for OpenAI rate limiting on API calls
            if isinstance(e, openai.error.RateLimitError):
                # if we hit the rate limit, send a cloudwatch alert and raise the error
                capture_metric(account['customer'], account['email'], function_name, correlation_id,
                               {"name": InfoMetrics.OPENAI_RATE_LIMIT, "value": 1, "unit": "None"})

            raise e

        result = response.choices[0].message.content

        if truncated:
            truncation = markdown_emphasize(f"Truncated input, discarded ~{OpenAIDefaults.boost_tuned_max_tokens - this_boost_tuned_max_tokens} words\n\n")
            result = truncation + result

        # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
        customer = account['customer']
        email = account['email']

        try:
            # Get the cost of the outputs and prior inputs - so we have visibiity into our cost per user API
            output_size = len(result)

            boost_cost = get_boost_cost(user_input_size + output_size)

            openai_output_tokens, openai_output_cost = get_openai_usage(result, False)
            openai_tokens = openai_input_tokens + openai_output_tokens
            openai_cost = openai_input_cost + openai_output_cost

            try:
                # update the billing usage for this analysis
                update_usage_for_text(account, prompt + user_input)
            except Exception:
                exception_info = traceback.format_exc().replace('\n', ' ')
                print(f"UPDATE_USAGE:FAILURE:{customer['name']}:{customer['id']}:{email}:{correlation_id}:Error updating ~${boost_cost} usage: ", exception_info)
                capture_metric(customer, email, function_name, correlation_id,
                               {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_cost, 5), "unit": "None"})

                pass  # Don't fail if we can't update usage / but that means we may have lost revenue

            capture_metric(customer, email, function_name, correlation_id,
                           {'name': CostMetrics.PROMPT_SIZE, 'value': prompt_size, 'unit': 'Count'},
                           {'name': CostMetrics.RESPONSE_SIZE, 'value': user_input_size, 'unit': 'Count'},
                           {'name': CostMetrics.OPENAI_INPUT_COST, 'value': round(openai_input_cost, 5), 'unit': 'None'},
                           {'name': CostMetrics.OPENAI_CUSTOMERINPUT_COST, 'value': round(openai_customerinput_cost, 5), 'unit': 'None'},
                           {'name': CostMetrics.OPENAI_OUTPUT_COST, 'value': round(openai_output_cost, 5), 'unit': 'None'},
                           {'name': CostMetrics.OPENAI_COST, 'value': round(openai_cost, 5), 'unit': 'None'},
                           {'name': CostMetrics.BOOST_COST, 'value': round(boost_cost, 5), 'unit': 'None'},
                           {'name': CostMetrics.OPENAI_INPUT_TOKENS, 'value': openai_input_tokens, 'unit': 'Count'},
                           {'name': CostMetrics.OPENAI_CUSTOMERINPUT_TOKENS, 'value': openai_customerinput_tokens, 'unit': 'Count'},
                           {'name': CostMetrics.OPENAI_OUTPUT_TOKENS, 'value': openai_output_tokens, 'unit': 'Count'},
                           {'name': CostMetrics.OPENAI_TOKENS, 'value': openai_tokens, 'unit': 'Count'})

        except Exception:
            exception_info = traceback.format_exc().replace('\n', ' ')
            print(f"{customer['name']}:{customer['id']}:{email}:{correlation_id}:Error capturing metrics: ", exception_info)
            pass  # Don't fail if we can't capture metrics

        return {
            "output": result,
            "truncated": truncated,
            "chunked": chunked
        }

    # used for calculating usage on user input. The return string is virtually useless in this format
    def collate_all_user_input(self, data):
        # remove any keys used for control of the processing, so we only charge for user input
        excluded_keys = ['model', 'top_p', 'temperature']
        input_list = [str(value) for key, value in data.items() if key not in excluded_keys]
        return ' '.join(input_list)
