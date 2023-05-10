# generic.py
import openai
import traceback
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import capture_metric, CostMetrics, InfoMetrics
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

    def process_code(self, data, account, context, correlation_id, prompt_format_args):
        prompt = self.prompts['main'].format(**prompt_format_args)
        role_system = self.prompts['role_system']

        print("prompt is")
        print(prompt)
        response = openai.ChatCompletion.create(
            model=OpenAIDefaults.boost_default_gpt_model,
            messages=[
                {
                    "role": "system",
                    "content": role_system
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=OpenAIDefaults.boost_tuned_max_tokens if OpenAIDefaults.boost_tuned_max_tokens != 0 else None
        )
        result = response.choices[0].message.content

        print('result is')
        print(result)
        # TODO: Insert the rest of the code for metrics and error handling
        # This part seems identical in both files, so you can move it into this class without modifications

        return result

