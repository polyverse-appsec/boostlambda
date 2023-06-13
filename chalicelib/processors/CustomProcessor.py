from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError

import json


class CustomProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'customprocess.prompt',
            'role_system': 'customprocess-role-system.prompt'
        })

    def generate_messages(self, data, prompt_format_args):
        code = data['code']
        customprompt = data['prompt']

        # if the user-provided prompt includes {code} block, then use that as the prompt
        if "{{code}}" in customprompt:
            prompt = customprompt.format(code=code, prompt=customprompt)
        # otherwise, use the default prompt to also inject {code} block into the prompt
        else:
            prompt = self.prompts['main'].format(code=code, prompt=customprompt)

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

        return this_messages, prompt

    def customprocess_code(self, data, account, function_name, correlation_id):
        # Extract the code from the json data
        code = data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for coding guidelines")

        # Extract the prompt from the json data
        prompt = data['prompt']
        if prompt is None:
            raise BadRequestError("Error: please provide a custom prompt to run against the code fragment")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {'code': code,
                                     'customprompt': prompt})

        return {"analysis": result}
