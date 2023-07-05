from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION


class ComplianceFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'compliance-function.prompt',
                         'compliance-function-role-system.prompt',
                         'compliance',
                         None,
                         'the type of bug, e.g. "privacy-leak", using standard issue types from GDPR, CCPA, ISO 27001, etc')

    def check_compliance(self, data, account, function_name, correlation_id):
        return self.check_code_with_function(data, account, function_name, correlation_id)
