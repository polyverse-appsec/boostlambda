from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION


class ComplianceFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'compliance-function.prompt',
                         'compliance-function-role-system.prompt',
                         'compliance',
                         'the type of bug, e.g. "privacy-leak", using standard bug types from the MITRE CWE taxonomy')

    def compliance_code(self, data, account, function_name, correlation_id):
        return self.check_code_with_function(data, account, function_name, correlation_id)
