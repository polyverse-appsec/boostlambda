from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import json
import math


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


class FunctionGenericProcessor(GenericProcessor):
    def __init__(self, api_version, main_prompt, system_prompt, function_name, custom_function_schema=None, bugTypeDescription=None):
        if custom_function_schema is not None:
            my_function_schema = custom_function_schema.copy()
        else:
            my_function_schema = report_bug_function.copy()
            my_function_schema['name'] = f"report_{function_name}_bugs"
            my_function_schema['description'] = f"reports {function_name} bugs in the code"
            my_function_schema['parameters']['properties']['bugs']['items']['properties']['bugType']['description'] = bugTypeDescription

        super().__init__(api_version, [
            ['main', main_prompt],
            ['system', system_prompt]],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
             'temperature': OpenAIDefaults.temperature_medium_with_explanation,
             'functions': [my_function_schema],
             'function_call': {"name": f"report_{function_name}_bugs"}},
            AnalysisOutputFormat.json)

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 80% of the buffer for the input, and 20% for the output, since the function call outputs are small
        # and we're much terser in output in this processor
        return math.floor(total_max * 0.8)

    # default is capturing bugs in the function output
    def process_function_output(self, result, log):

        bugs = []
        # if we get here, we have a function call in the results array.  loop through each of the results and add the array of arguments to the bugs array
        # result['results'][0]['message']['function_call']['arguments'] is a JSON formatted string. parse it into a JSON object.  it may be corrupt, so ignore
        # any errors
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

    def check_code_with_function(self, data, account, function_name, correlation_id):

        # Extract the code from the json data
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        prompt_format_args = {self.get_chunkable_input(): code}
        if 'inputMetadata' in data:
            inputMetadata = json.loads(data['inputMetadata'])
            lineNumberBase = inputMetadata['lineNumberBase']
            prompt_format_args['lineNumberBase'] = f"When identifying source numbers for issues, treat the first line of the code as line number {lineNumberBase + 1}"

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code})

        # if result['messages'] has a field 'function_call', then we have the data for a function call
        if 'function_call' not in result['results'][0]['message']:
            print(f"{function_name}:{account['email']}:{correlation_id}:No function call found in OpenAI response")
            return {"details": []}

        def log(message):
            print(f"{function_name}:{account['email']}:{correlation_id}:{message}")

        return self.process_function_output(result, log)
