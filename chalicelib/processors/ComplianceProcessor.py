from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION


class ComplianceProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'compliance.prompt',
            'role_system': 'compliance-role-system.prompt'
        })

    def get_chunkable_input(self) -> str:
        return 'code'

    def compliance_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()]

        result = self.process_input(data, account, function_name, correlation_id, {self.get_chunkable_input(): code})

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
