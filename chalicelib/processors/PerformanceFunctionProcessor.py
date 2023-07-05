from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION


class PerformanceFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'performance-function.prompt',
                         'performance-function-role-system.prompt',
                         'performance',
                         None,
                         'the type of issue, e.g. "Memory", "Disk", using one of the following types: CPU, Memory, Disk, Network and Datastore')

    def check_performance(self, data, account, function_name, correlation_id):
        return self.check_code_with_function(data, account, function_name, correlation_id)
