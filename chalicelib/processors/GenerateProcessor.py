from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError


class GenerateProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'convert.prompt',
            'role_system': 'convert-role-system.prompt',
            'role_assistant': 'convert-role-assistant.prompt',
            'role_user': 'convert-role-user.prompt'
        })

    def convert_code(self, data, account, function_name, correlation_id):
        # Extract the explanation and original_code from the json data
        explanation = data.get('explanation')
        if explanation is None:
            raise BadRequestError("Error: please provide the initial code explanation")

        original_code = data.get('originalCode')
        if original_code is None:
            raise BadRequestError("Error: please provide the original code")

        # The output language is optional; if not set, then default to Python
        outputlanguage = data.get('language', 'python')

        result = self.process_input(data, account, function_name, correlation_id,
                                    {'explanation': explanation,
                                     'original_code': original_code,
                                     'language': outputlanguage})

        return {"code": result}
