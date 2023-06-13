from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION


class BlueprintProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'role_system': 'blueprint-role-system.prompt',
            'seed': 'blueprint-seed.prompt',
            'update': 'blueprint-update.prompt'
        })

    def generate_messages(self, data, prompt_format_args):

        # Extract the code from the json data
        code = data['code']

        # Extract the prior blueprint from the json data
        if 'blueprint' in data:
            prior_blueprint = data['blueprint']
            # If there is no prior blueprint, set the prompt is creating the seed blueprint from the ingested code
            if prior_blueprint is None:
                prompt = self.prompts['seed'].format(code=code)
            else:
                prompt = self.prompts['update'].format(code=code, prior_blueprint=prior_blueprint)
        else:
            prompt = self.prompts['seed'].format(code=code)

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

    def blueprint_code(self, data, account, function_name, correlation_id):

        result = self.process_input(data, account, function_name, correlation_id, {})

        return {"blueprint": result}
