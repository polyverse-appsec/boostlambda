from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from typing import Tuple
from chalicelib.usage import OpenAIDefaults


class BlueprintProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'role_system': 'blueprint-role-system.prompt',
            'seed': 'blueprint-seed.prompt',
            'update': 'blueprint-update.prompt'
        }, {'model': OpenAIDefaults.boost_default_gpt_model,
            'temperature': OpenAIDefaults.temperature_medium_with_explanation})

    def get_chunkable_input(self) -> str:
        return 'code'

    def generate_prompt(self, data, prompt_format_args):
        # Extract the prior blueprint from the json data
        if 'blueprint' in data:
            prompt_format_args['prior_blueprint'] = data['blueprint']
            # If there is no prior blueprint, set the prompt is creating the seed blueprint from the ingested code
            if 'prior_blueprint' not in data:
                return self.prompts['seed'].format(**prompt_format_args)
            else:
                prompt_format_args['prior_blueprint'] = data['prior_blueprint']
                return self.prompts['update'].format(**prompt_format_args)
        else:
            return self.prompts['seed'].format(**prompt_format_args)

    def generate_messages(self, data, prompt_format_args) -> Tuple[list[dict[str, any]]]:

        # Extract the code from the json data
        prompt_format_args[self.get_chunkable_input()] = data[self.get_chunkable_input()]

        # if we aren't doing chunking, then just erase the tag from the prompt completely
        if 'chunking' not in prompt_format_args:
            prompt_format_args['chunking'] = ' '

        prompt = self.generate_prompt(data, prompt_format_args)

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

        return this_messages

    def blueprint_code(self, data, account, function_name, correlation_id):

        result = self.process_input(data, account, function_name, correlation_id, {})

        return {
            "blueprint": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
