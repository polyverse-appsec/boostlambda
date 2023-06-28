from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults, num_tokens_from_string, decode_string_from_input, max_tokens_for_model

import json
import math


class CustomProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'customprocess.prompt'],
            ['system', 'customprocess-role-system.prompt']],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
             'temperature': OpenAIDefaults.temperature_medium_with_explanation})

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and 10% for the output
        return math.floor(total_max * 0.8)

    # we're only going to use 75% of our buffer for system messages (e.g. background info)
    def calculate_system_message_token_buffer(self, total_max) -> int:
        return math.floor(self.calculate_input_token_buffer(total_max) * 0.75)

    def generate_messages(self, data, prompt_format_args):
        if 'messages' in data:
            this_messages = json.loads(data['messages'])
        else:
            result = super().generate_messages(data, prompt_format_args)

            customprompt = data['prompt']
            # if the user-provided prompt includes {code} block, then use that as the prompt
            if "{{code}}" in customprompt:
                code = data['code']
                prompt = customprompt
                prompt = super.safe_format(prompt, code=code, prompt=customprompt)

                for message in reversed(result):
                    if message['role'] != 'user':
                        raise Exception('Unexpected last message role: ' + message['role'])
                    message['content'] = prompt
                    break

            if 'role_system' in data:
                for message in result:
                    if message['role'] != 'system':
                        raise Exception('Unexpected last message role: ' + message['role'])
                    message['content'] = data['role_system']
                    break

        # in case the messages (system) are too long, we'll truncate them to the sys token buffer
        # in case we receive messages with no content, discard them
        new_messages = []
        discarded_messages = []
        for message in this_messages:
            if 'content' not in message or message['content'] == '':
                discarded_messages.append(message)
                continue  # Skip this iteration and move to next message
            if message['role'] == 'system':
                sys_token_count, sys_tokens = num_tokens_from_string(message['content'])
                retained_tokens = self.calculate_system_message_token_buffer(max_tokens_for_model(data.get('model')))
                if sys_token_count > retained_tokens:
                    message['content'] = decode_string_from_input(sys_tokens[:retained_tokens])
                    print(f"{self.__class__.__name__}:Truncation:"
                          f"System input discarded {sys_token_count - retained_tokens} tokens")
            new_messages.append(message)
        this_messages = new_messages

        if len(discarded_messages) > 0:
            print(f"{self.__class__.__name__}:Truncation:"
                  f"Discarded {len(discarded_messages)} messages with no content")
        this_messages = new_messages

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
