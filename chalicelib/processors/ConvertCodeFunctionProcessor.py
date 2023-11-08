from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError

import math


convert_code = {
    "name": "convert_code",
    "description": "The API that will convert code from one language to another",
    "parameters": {
        "type": "object",
        "properties": {
            "convertedCode": {
                "type": "string",
                "description": "The code that was converted"
            },
            "issuesDuringConversion": {
                "type": "array",
                "description": "List of errors, warnings or issues encountered while performing conversion.",
                "items": {
                    "type": "string",
                    "description": "An error or warning or problem with performing a perfect logic conversion or an issue requiring followup."
                }
            },
            "convertedFileExtension": {
                "type": "string",
                "description": "The file extension for the converted filed"
            },
            "recommendedConvertedFilenameBase": {
                "type": "string",
                "description": "The recommended filename base for the converted file"
            },
        }
    }
}


class ConvertCodeFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'convert-code-function.prompt'],

                          # shared with the non-function version
                          ['system', 'convert-role-system.prompt'],
                          ['assistant', 'convert-role-assistant.prompt'],
                          ['user', 'convert-role-user.prompt']],
                         'convert_code',
                         convert_code)

    def calculate_input_token_buffer(self, total_max) -> int:
        # we need at least 40% of the input buffer for the input, and the last 60% for the converted code
        # we use a little more for output, since the output should have well formed comments and spacing
        # and the converted language may be more verbose than the original language
        return math.floor(total_max * 0.4)

    def get_function_definition(self):
        return convert_code

    # no properties are required by default - since we can collect a list of issues
    def is_required_property(self, prop):
        return False

    def validate_response_properties(self, arguments, required_properties, log):
        success = super().validate_response_properties(arguments, required_properties, log)
        if success == super().function_response_failure:
            return success

        # if we have issues during conversion, the process ran to completion
        if 'issuesDuringConversion' in arguments and len(arguments['issuesDuringConversion']) > 0:
            return super().function_response_success

        # of if we have converted code
        if 'convertedCode' in arguments:
            return super().function_response_success

        return super().function_response_failure

    # we are going to chunk the explanation, since its bigger than the code presumptively
    # However - realistically, we should be chunking both. But they segment independently - e.g.
    # 1 line of code could be a paragraph of explanation. Harder to slice and dice them blindly
    # into coordinated chunks. But there's a good chance chunking one or the other only will break
    # both the conversion and ability to chunk (e.g. if the code is over the buffer size, and we chunk
    # only the explanation, we'll never be able to process the code, and vice versa)
    def get_chunkable_input(self) -> str:
        return 'explanation'

    def collect_inputs_for_processing(self, data):
        # Extract the explanation and code from the json data
        explanation = data.get(self.get_chunkable_input())
        if explanation is None:
            raise BadRequestError("Error: please provide the initial code explanation")

        code = data.get('code') if 'code' in data else None
        if code is None:
            raise BadRequestError("Error: please provide the original code")

        # The output language is optional; if not set, then default to existing programming language
        outputlanguage = data.get('language', 'programming')

        originalFilename = data.get('originalFilename') if 'originalFilename' in data else None
        if originalFilename is None:
            raise BadRequestError("Error: please provide the original filename")

        prompt_format_args = {self.get_chunkable_input(): explanation,
                              "code": code,
                              "originalFilename": originalFilename,
                              "language": outputlanguage}

        return prompt_format_args

    def convert_code(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
