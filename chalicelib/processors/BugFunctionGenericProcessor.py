from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalice import BadRequestError

import json


# the live version does not use startCol and endCol. The line number is calculated from the original line number of the chunk if given,
# but is it not always precise. there's no need to complicate the job of the AI with startCol and endCol, which are not always precise
report_bug_function = {
    "name": "",
    "description": "",
    "parameters": {
        "type": "object",
        "properties": {
            "bugs": {
                "type": "array",
                "description": "the list of bugs found in the code",
                "items": {
                    "type": "object",
                    "properties": {
                        "lineNumber": {
                            "type": "integer",
                            "description": "the line number where the bug begins, calculated from the original line number of the chunk if given"
                        },
                        "severity": {
                            "type": "integer",
                            "description": "the severity of the bug, 1-10, 10 being the most severe"
                        },
                        "bugType": {
                            "type": "string",
                            "description": ""
                        },
                        "description": {
                            "type": "string",
                            "description": "a description in markdown format of why the bug is a bug and how it might be exposed",
                        },
                        "solution": {
                            "type": "string",
                            "description": "the solution description in markdown format of how to fix the bug",
                        }
                    }
                }
            }
        },
    }
}


class BugFunctionGenericProcessor(FunctionGenericProcessor):
    def __init__(self, api_version, prompts, function_name, bugTypeDescription=None):
        my_function_schema = report_bug_function.copy()

        if function_name is None:
            raise BadRequestError("Error: please provide a function name to run against the code fragment")

        if bugTypeDescription is None:
            raise BadRequestError("Error: please provide a bug type description to categorize the bugs found in the code")

        function_call = f"report_{function_name}_bugs"
        my_function_schema['name'] = function_call
        my_function_schema['description'] = f"reports {function_name} bugs in the code"
        my_function_schema['parameters']['properties']['bugs']['items']['properties']['bugType']['description'] = bugTypeDescription

        super().__init__(api_version,
                         prompts,
                         function_call,
                         my_function_schema)

    def get_function_definition(self):
        return report_bug_function

    # default is capturing bugs in the function output
    def process_function_output(self, result, log):
        response = super().process_function_output(result, log)

        # bug processor collects only bugs, so flatten the details to bugs
        response["details"] = response["details"]["bugs"] if "bugs" in response["details"] else []

        response["status"] = "bugsfound" if len(response['details']) > 0 else "nobugsfound"

        return response

    def collect_inputs_for_processing(self, data):
        prompt_format_args = super().collect_inputs_for_processing(data)

        if 'inputMetadata' in data:
            inputMetadata = json.loads(data['inputMetadata'])
            lineNumberBase = inputMetadata['lineNumberBase'] if 'lineNumberBase' in inputMetadata else 0
            prompt_format_args['lineNumberBase'] = f"When identifying source numbers for issues," \
                                                   f" treat the first line of the code as line number {lineNumberBase}"

        return prompt_format_args
