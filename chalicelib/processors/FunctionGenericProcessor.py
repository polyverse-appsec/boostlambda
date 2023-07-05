from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import math


class FunctionGenericProcessor(GenericProcessor):
    def __init__(self, api_version, main_prompt, system_prompt, function_call, custom_function_schema):
        my_function_schema = custom_function_schema.copy()

        super().__init__(api_version, [
            ['main', main_prompt],
            ['system', system_prompt]],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
             'temperature': OpenAIDefaults.temperature_medium_with_explanation,
             'functions': [my_function_schema],
             'function_call': {"name": f"{function_call}"}},
            AnalysisOutputFormat.json)

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 80% of the buffer for the input, and 20% for the output, since the function call outputs are small
        # and we're much terser in output in this processor
        return math.floor(total_max * 0.8)

    def process_function_output(self, result, log):
        raise Exception("process_function_output Not implemented")

    def collect_inputs_for_processing(self, data):
        # Extract the code from the json data
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        prompt_format_args = {self.get_chunkable_input(): code}

        return prompt_format_args

    def process_input_with_function_output(self, data, account, function_name, correlation_id):

        prompt_format_args = self.collect_inputs_for_processing(data)

        result = self.process_input(data, account, function_name, correlation_id,
                                    prompt_format_args)

        # if result['messages'] has a field 'function_call', then we have the data for a function call
        if 'function_call' not in result['results'][0]['message']:
            print(f"{function_name}:{account['email']}:{correlation_id}:No function call found in OpenAI response")
            return {"details": []}

        def log(message):
            print(f"{function_name}:{account['email']}:{correlation_id}:{message}")

        return self.process_function_output(result, log)
