from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor

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
                            "description": "the line number where the bug begins, caculated from the original line number of the chunk if given"
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
    def __init__(self, api_version, main_prompt, system_prompt, function_name, bugTypeDescription=None):
        my_function_schema = report_bug_function.copy()

        function_call = f"report_{function_name}_bugs"

        my_function_schema['name'] = function_call
        my_function_schema['description'] = f"reports {function_name} bugs in the code"
        my_function_schema['parameters']['properties']['bugs']['items']['properties']['bugType']['description'] = bugTypeDescription

        super().__init__(api_version,
                         main_prompt,
                         system_prompt,
                         function_call,
                         my_function_schema)

    # default is capturing bugs in the function output
    def process_function_output(self, result, log):

        bugs = []
        # if we get here, we have a function call in the results array.  loop through each of the results and
        # add the array of arguments to the bugs array result['results'][0]['message']['function_call']['arguments']
        # is a JSON formatted string. parse it into a JSON object.  it may be corrupt, so ignore any errors
        for r in result['results']:
            try:
                json_bugs = json.loads(r['message']['function_call']['arguments'])
                bugs.extend(json_bugs["bugs"])
            except Exception as e:
                log(f"Error parsing function call arguments: {e}")
                pass

        if json_bugs["bugs"] is None or len(json_bugs["bugs"]) == 0:

            log("No bugs found with OpenAI reporting functional output")

        if len(bugs) > 0:
            return {
                "status": "bugsfound",
                "details": bugs
            }
        else:
            return {
                "status": "nobugsfound",
                "details": []
            }

    def collect_inputs_for_processing(self, data):
        prompt_format_args = super().collect_inputs_for_processing(data)

        if 'inputMetadata' in data:
            inputMetadata = json.loads(data['inputMetadata'])
            lineNumberBase = inputMetadata['lineNumberBase'] if 'lineNumberBase' in inputMetadata else 0
            prompt_format_args['lineNumberBase'] = f"When identifying source numbers for issues," \
                                                   f" treat the first line of the code as line number {lineNumberBase + 1}"

        return prompt_format_args
