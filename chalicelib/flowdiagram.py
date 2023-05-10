from chalicelib.genericprocessor import GenericProcessor
from chalicelib.version import API_VERSION

class FlowDiagramProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'flowdiagram.prompt',
            'role_system': 'flowdiagram-role-system.prompt'
        })

    def flowdiagram_code(self, code, account, context, correlation_id):
        return self.process_code(code, account, context, correlation_id, {'code': code})
