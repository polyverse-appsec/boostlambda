from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import json


class CustomProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'customprocess.prompt',
            'role_system': 'customprocess-role-system.prompt'
        }, {'model': OpenAIDefaults.boost_default_gpt_model,
            'temperature': OpenAIDefaults.default_temperature})

    def get_chunkable_input(self) -> str:
        return 'code'

    def generate_prompt(self, _, prompt_format_args):
        # if the user-provided prompt includes {code} block, then use that as the prompt
        if "{{code}}" in prompt_format_args['customprompt']:
            return prompt_format_args['customprompt'].format(prompt_format_args)
        # otherwise, use the default prompt to also inject {code} block into the prompt
        else:
            return self.prompts['main'].format(prompt_format_args)

    def generate_messages(self, data, prompt_format_args):
        prompt_format_args[self.get_chunkable_input()] = data[self.get_chunkable_input()]
        prompt_format_args['customprompt'] = data['prompt']

        # if we aren't doing chunking, then just erase the tag from the prompt completely
        if 'chunking' not in prompt_format_args:
            prompt_format_args['chunking'] = ' '

        prompt = self.generate_prompt(prompt_format_args)

        if 'role_system' in data:
            this_role_system = data['role_system']
        else:
            this_role_system = self.prompts['role_system']

        if 'messages' in data:
            this_messages = json.loads(data['messages'])
        else:
            this_messages = [
                {
                    "role": "system",
                    "content": this_role_system
                },
                {
                    "role": "user",
                    "content": prompt
                }]

        return this_messages

    def customprocess_code(self, data, account, function_name, correlation_id):
        # Extract the code from the json data
        code = data[self.get_chunkable_input()]
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for coding guidelines")

        # Extract the prompt from the json data
        prompt = data['prompt']
        if prompt is None:
            raise BadRequestError("Error: please provide a custom prompt to run against the code fragment")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code,
                                     'customprompt': prompt})

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
