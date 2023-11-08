from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults, num_tokens_from_string

import json
import math


class FunctionGenericProcessor(GenericProcessor):
    def __init__(self, api_version, prompts, function_call, custom_function_schema, custom_params=None):
        my_function_schema = custom_function_schema.copy()

        default_params = {
            'model': OpenAIDefaults.boost_default_gpt_model,
            'temperature': OpenAIDefaults.temperature_medium_with_explanation,
            'functions': [my_function_schema],
            'function_call': {"name": f"{function_call}"}}

        my_default_params = default_params.copy()

        # Update my_default_params with values from custom_params (if provided)
        if custom_params:
            my_default_params.update(custom_params)

        super().__init__(api_version,
                         prompts,
                         None,
                         my_default_params,
                         AnalysisOutputFormat.json)

        # Validate that the function definition has all the necessary properties
        # We check now, so we don't fail suddenly during post-processing of analysis results
        function_definition = self.get_function_definition()
        if not function_definition or "parameters" not in function_definition or "properties" not in function_definition["parameters"]:
            print("Error: The function definition is missing necessary properties.")
            raise BadRequestError("Error: The function definition is missing necessary properties.")

        # ensure the function definition will fit in the input buffer - excluding system buffer
        # we check the function definition after params, since we need the chosen model to check
        function_definition_token_length = num_tokens_from_string(json.dumps(function_definition), my_default_params['model'])[0]
        potential_function_definition_token_buffer = self.calculate_input_token_buffer(self.get_default_max_tokens()) - self.calculate_system_message_token_buffer(self.get_default_max_tokens())
        if function_definition_token_length > potential_function_definition_token_buffer:
            print(f"Error: The function definition is too large to fit in the input buffer. Function definition length: {function_definition_token_length}, Input buffer length: {potential_function_definition_token_buffer}")
            raise BadRequestError("Error: The function definition is too large to fit in the input buffer.")

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 80% of the buffer for the input, and 20% for the output, since the function call outputs are small
        # and we're much terser in output in this processor
        return math.floor(total_max * 0.8)

    def get_function_definition(self):
        raise NotImplementedError("Function Definition not implemented")

    # default is a pure replacement of the property in processing sequence (last one wins)
    def merge_functional_result(self, arguments, prop, json_arguments):
        if prop not in json_arguments:
            return

        # If the value in json_arguments[prop] is a string or number
        if isinstance(json_arguments[prop], list):
            if prop not in arguments or arguments[prop] is None:
                arguments[prop] = json_arguments[prop]
            else:
                arguments[prop].extend(json_arguments[prop])
        else:
            arguments[prop] = json_arguments[prop]

    def process_function_output(self, result, log):

        # Given the derived class structure, you can extract the required properties
        required_properties = self.get_function_definition()["parameters"]["properties"]

        arguments = {}

        # Loop through each of the results and add the array of arguments to the properties array
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
                        self.merge_functional_result(arguments, prop, json_arguments)
                    else:
                        default_value = [] if required_properties[prop]["type"] == "array" else ""
                        arguments[prop] = default_value

            except Exception as e:
                log(f"Error parsing function call arguments: {e}")
                pass

        # Check if all required properties exist in the arguments
        success = self.validate_response_properties(arguments, required_properties, log)

        return {
            "status": success,
            "details": arguments
        }

    function_response_success = 1
    function_response_failure = 0

    def validate_response_properties(self, arguments, required_properties, log):
        success = self.function_response_success
        for prop in required_properties:
            if prop not in arguments or (isinstance(arguments[prop], (list, str)) and not arguments[prop]):
                log(f"{prop} was not generated or is empty")
                if not self.is_required_property(prop):
                    continue
                success = self.function_response_failure
        return success

    def is_required_property(self, prop):
        return True

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

    def handleFinalCallError(self, e, input_tokens, log):
        # if we timed out trying to make the calls, return them as "incomplete" - so we can gracefully handle it
        if not isinstance(e, (TimeoutError)):
            return None

        log(f"OpenAI call timed out retrying, giving up - and treating an incomplete successful call: {str(e)}")

        return dict(
            message={'function_call': None},  # we only set this flag so callers know we're a function-based call
            response=None,
            error=e,
            finish=None,
            input_tokens=input_tokens,
            output_tokens=0)
