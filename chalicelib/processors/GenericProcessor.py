# generic.py
import openai
import traceback
from .. import pvsecret
import os
from chalicelib.telemetry import capture_metric, InfoMetrics, CostMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults
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

    def process_input(self, data, account, function_name, correlation_id, prompt_format_args):
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

        if OpenAIDefaults.boost_tuned_max_tokens != 0:
            params["max_tokens"] = OpenAIDefaults.boost_tuned_max_tokens

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

        # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
        customer = account['customer']
        email = account['email']

        try:
            # Get the cost of the prompting - so we have visibiity into our cost per user API
            prompt_size = len(this_messages)
            user_input = self.collate_all_user_input(data)
            user_input_size = len(user_input)
            boost_cost = get_boost_cost(prompt_size + user_input_size)
            openai_input_tokens, openai_input_cost = get_openai_usage(this_messages)
            openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(user_input)
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

        return result

    # used for calculating usage on user input. The return string is virtually useless in this format
    def collate_all_user_input(self, data):
        # remove any keys used for control of the processing, so we only charge for user input
        excluded_keys = ['model', 'top_p', 'temperature']
        input_list = [str(value) for key, value in data.items() if key not in excluded_keys]
        return ' '.join(input_list)
