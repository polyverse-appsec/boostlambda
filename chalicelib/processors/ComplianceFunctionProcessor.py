from chalicelib.processors.BugFunctionGenericProcessor import BugFunctionGenericProcessor
from chalicelib.version import API_VERSION


class ComplianceFunctionProcessor(BugFunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'compliance-function.prompt'],
                          ['system', 'compliance-function-role-system.prompt']],
                         'compliance',
                         'the type of bug, e.g. "privacy-leak", using standard issue types from GDPR, CCPA, ISO 27001, etc')

    def check_compliance(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
