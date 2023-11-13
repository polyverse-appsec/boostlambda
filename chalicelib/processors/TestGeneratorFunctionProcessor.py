from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError

import math


generate_tests = {
    "name": "generate_tests",
    "description": "The API that will generate tests for a block of code",
    "parameters": {
        "type": "object",
        "properties": {
            "testFramework": {
                "type": "string",
                "description": "The test framework to use for generating tests"
            },
            "testProgrammingLanguage": {
                "type": "string",
                "description": "The programming language to use for generating tests"
            },
            "recommendedTestLanguageFileExtension": {
                "type": "string",
                "description": "The recommended file extension for the test file"
            },
            "generatedTestCases": {
                "type": "array",
                "description": "the list of tests generated",
                "items": {
                    "type": "object",
                    "description": "generated test case",
                    "properties": {
                        "sourceCode": {
                            "type": "string",
                            "description": ""
                        },
                        "testType": {
                            "type": "string",
                            "description": ""
                        },
                        "testFileName": {
                            "type": "string",
                            "description": "",
                        }
                    }
                }
            },
        }
    }
}


class TestGeneratorFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'testgen-function.prompt'],

                          # shared with the non-function version
                          ['system', 'testgen-role-system.prompt']],
                         'generate_tests',
                         generate_tests)

    def calculate_input_token_buffer(self, total_max) -> int:
        # we need at least 30% of the input buffer for the input, and the last 70% for the generated tests
        # we use more for output, since the mosts test cases take more code than the original source code
        return math.floor(total_max * 0.3)

    def get_function_definition(self):
        return generate_tests

    # no properties are required by default - since we can collect a list of issues
    def is_required_property(self, prop):
        return False

    def validate_response_properties(self, arguments, required_properties, log):
        success = super().validate_response_properties(arguments, required_properties, log)
        if success == super().function_response_failure:
            return success

        # if we have issues during conversion, the process ran to completion
        if 'issuesDuringTestGeneration' in arguments and len(arguments['issuesDuringTestGeneration']) > 0:
            return super().function_response_success

        # of if we have converted code
        if 'generatedTests' in arguments:
            return super().function_response_success

        return super().function_response_failure

    def get_chunkable_input(self) -> str:
        return 'code'

    def collect_inputs_for_processing(self, data):
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide the code to test")

        outputlanguage = data['language'] if 'language' in data else None
        if outputlanguage is None:
            outputlanguage = "language of this code"

        testType = data['testType'] if 'testType' in data else None
        if testType is None:
            testType = "unit, functional, negative, fuzzing, performance, stress, platform, and regression"

        framework = data['framework'] if 'framework' in data else None
        if framework is None:
            if outputlanguage == "python":
                framework = "pytest"
            else:
                framework = "the best matched framework"

        prompt_format_args = {self.get_chunkable_input(): code,
                              "language": outputlanguage,
                              "framework": framework,
                              "testType": testType}

        return prompt_format_args

    def generate_tests(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
