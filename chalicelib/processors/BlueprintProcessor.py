from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError


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

    def blueprint_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide the original code")

        result = self.process_input(data, account, function_name, correlation_id, {'code': code})

        return {
            "blueprint": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
