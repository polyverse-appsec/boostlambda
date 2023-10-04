from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import json
import math


class FunctionGenericProcessor(GenericProcessor):
    def __init__(self, api_version, prompts, function_call, custom_function_schema):
        my_function_schema = custom_function_schema.copy()

        # Validate that the function definition has all the necessary properties
        # We check now, so we don't fail suddenly during post-processing of analysis results
        function_definition = self.get_function_definition()
        if not function_definition or "parameters" not in function_definition or "properties" not in function_definition["parameters"]:
            print("Error: The function definition is missing necessary properties.")
            raise BadRequestError("Error: The function definition is missing necessary properties.")

        super().__init__(api_version,
                         prompts,
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

    def get_function_definition(self):
        raise NotImplementedError("Function Definition not implemented")

    def process_function_output(self, result, log):

        # Given the derived class structure, you can extract the required properties
        required_properties = self.get_function_definition()["parameters"]["properties"]

        arguments = {}

        # Loop through each of the results and add the array of arguments to the bugs array
        for r in result['results']:
            # Validate that the necessary properties exist in r
            if not r or "message" not in r or "function_call" not in r["message"] or "arguments" not in r["message"]["function_call"]:
                log("Error: The result item is missing necessary properties.")
                continue

            try:
                json_arguments = json.loads(r['message']['function_call']['arguments'])

                # Iterate through the required properties to check if they exist in the arguments
                for prop in required_properties:
                    if prop in json_arguments:
                        arguments[prop] = json_arguments[prop]
                    else:
                        default_value = [] if required_properties[prop]["type"] == "array" else ""
                        arguments[prop] = default_value

            except Exception as e:
                log(f"Error parsing function call arguments: {e}")
                pass

        # Check if all required properties exist in the arguments
        success = 1
        for prop in required_properties:
            if prop not in arguments or (isinstance(arguments[prop], (list, str)) and not arguments[prop]):
                log(f"{prop} was not generated or is empty")
                success = 0

        return {
            "status": success,
            "details": arguments
        }

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
