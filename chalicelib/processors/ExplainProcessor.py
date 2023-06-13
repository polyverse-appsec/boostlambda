from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION


class ExplainProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'explain.prompt',
            'role_system': 'explain-role-system.prompt'
        })

    def explain_code(self, data, account, function_name, correlation_id):
        code = data['code']

        result = self.process_input(data, account, function_name, correlation_id,
                                    {'code': code})

        return {
            "explanation": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }

