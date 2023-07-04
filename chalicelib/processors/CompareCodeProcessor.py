from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError


class CompareCodeProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'compare-code.prompt'],
            ['system', 'compare-code-role-system.prompt'],
            ['system', 'compare-code-original-code-role-system.prompt']],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
             'temperature': OpenAIDefaults.temperature_terse_and_accurate})

    def get_chunkable_input(self) -> str:
        return 'code'

    def compare_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide the original code")

        code_compare = data['code_compare'] if 'code_compare' in data else None
        if code_compare is None:
            raise BadRequestError("Error: please provide the comparison code")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code,
                                     'code_compare': code_compare})

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
