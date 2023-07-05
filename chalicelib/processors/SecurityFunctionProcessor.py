from chalicelib.processors.BugFunctionGenericProcessor import BugFunctionGenericProcessor
from chalicelib.version import API_VERSION


class SecurityFunctionProcessor(BugFunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'security-function.prompt',
                         'security-function-role-system.prompt',
                         'security',
                         'the type of bug, e.g. "sql-injection", using standard bug types from the MITRE CWE taxonomy')

    def secure_code(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
