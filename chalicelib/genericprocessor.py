# generic.py
import openai
# import traceback
from . import pvsecret
import os
from chalicelib.telemetry import capture_metric, InfoMetrics  # , CostMetrics
from chalicelib.usage import OpenAIDefaults  # , get_openai_usage, get_boost_cost,
# from chalicelib.payments import update_usage_for_text

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

    def process_code(self, data, account, function_name, correlation_id, prompt_format_args):
        prompt = self.prompts['main'].format(**prompt_format_args)
        role_system = self.prompts['role_system']

        # enable user to override the model to gpt-3 or gpt-4
        model = OpenAIDefaults.boost_default_gpt_model
        if 'model' in data:
            model = data['model']

        params = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": role_system
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]}

        if OpenAIDefaults.boost_tuned_max_tokens != 0:
            params["max_tokens"] = OpenAIDefaults.boost_tuned_max_tokens

        # https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
        if 'top_p' in data:
            params["top_p"] = float(data['top_p'])
        elif 'temperature' in data:
            params["temperature"] = float(data['temperature'])

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

        # TODO: Insert the rest of the code for metrics and error handling
        # This part seems identical in both files, so you can move it into this class without modifications

        return result
