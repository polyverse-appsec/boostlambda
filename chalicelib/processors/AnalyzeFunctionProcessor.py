from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError


class AnalyzeFunctionProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'analyze.prompt',
            'role_system': 'analyze-role-system.prompt'
        })

    def get_chunkable_input(self) -> str:
        return 'code'

    def analyze_code(self, data, account, function_name, correlation_id):

        # Extract the code from the json data
        code = data[self.get_chunkable_input()]
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code})

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
