from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION


class CodingGuidelinesProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'guidelines.prompt',
            'role_system': 'guidelines-role-system.prompt'
        })

    def checkguidelines_code(self, data, account, function_name, correlation_id):
        code = data['code']

        result = self.process_input(data, account, function_name, correlation_id, {'code': code})

        return {"analysis": result}
