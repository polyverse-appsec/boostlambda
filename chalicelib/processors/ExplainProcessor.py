from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults


class ExplainProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'explain.prompt',
            'role_system': 'explain-role-system.prompt',
        }, {'model': OpenAIDefaults.boost_default_gpt_model,
            'temperature': OpenAIDefaults.temperature_verbose_and_explanatory})

    def get_chunkable_input(self) -> str:
        return 'code'

    def explain_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()]

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code})

        return {
            "explanation": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
