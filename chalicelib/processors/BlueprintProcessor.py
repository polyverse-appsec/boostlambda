from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults


class BlueprintProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'blueprint-seed.prompt'],
            ['system', 'blueprint-role-system.prompt']],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
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

    def generate_messages(self, data, prompt_format_args) -> list[dict[str, any]]:

        result = super().generate_messages(data, prompt_format_args)

        prompt = self.generate_prompt(data, prompt_format_args)

        for message in reversed(result):
            if message['role'] != 'user':
                raise Exception('Unexpected last message role: ' + message['role'])
            message['content'] = prompt
            break

        return result

    def blueprint_code(self, data, account, function_name, correlation_id):

        result = self.process_input(data, account, function_name, correlation_id, {})

        return {
            "blueprint": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
