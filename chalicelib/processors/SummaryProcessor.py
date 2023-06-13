import math

from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION


class SummarizeProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'summarize.prompt',
            'role_system': 'summarize-role-system.prompt'
        })

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and 10% for the output
        return math.floor(total_max * 0.9)

    def summarize_inputs(self, data, account, function_name, correlation_id):
        inputs = data['inputs']
        analysis_type = data['analysis_type']
        analysis_label = data['analysis_label']

        result = self.process_input(data, account, function_name, correlation_id,
                                    {'inputs': inputs,
                                     'analysis_type': analysis_type,
                                     'analysis_label': analysis_label})

        return {"analysis": result['output'],
                "truncated": result['truncated'],
                "chunked": result['chunked'],
                "analysis_type": analysis_type,
                "analysis_label": analysis_label}
