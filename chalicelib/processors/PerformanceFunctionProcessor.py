from chalicelib.processors.BugFunctionGenericProcessor import BugFunctionGenericProcessor
from chalicelib.version import API_VERSION


class PerformanceFunctionProcessor(BugFunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'performance-function.prompt',
                         'performance-function-role-system.prompt',
                         'performance',
                         'the type of issue, e.g. "Memory", "Disk", using one of the following types: CPU, Memory, Disk, Network and Datastore')

    def check_performance(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
