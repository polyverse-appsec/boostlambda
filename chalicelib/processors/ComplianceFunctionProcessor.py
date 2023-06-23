from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import json
import math


report_bug_function_old = {
    "name": "report_compliance_bugs",
    "description": "reports compliance bugs in the code",
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
                        "startCol": {
                            "type": "integer",
                            "description": "the column index on the line where the bug begins"
                        },
                        "endCol": {
                            "type": "integer",
                            "description": "the column index one the line where the bug ends "
                        },
                        "severity": {
                            "type": "integer",
                            "description": "the severity of the bug, 1-10, 10 being the most severe"
                        },
                        "bugType": {
                            "type": "string",
                            "description": "the type of bug, e.g. 'privacy leak', using standard bug types from the MITRE CWE taxonomy"
                        },
                        "description": {
                            "type": "string",
                            "description": "a description in markdown format of why the bug is a bug and how it might be exploited",
                        },
                        "solution": {
                            "type": "string",
                            "description": "the solution description in markdown format of how to fix the bug",
                        }
                    }
                }
            }
        },
        "required": ["bugs"]
    }
}

# the live version does not use startCol and endCol. The line number is calculated from the original line number of the chunk if given,
# but is it not always precise. there's no need to complicate the job of the AI with startCol and endCol, which are not always precise
report_bug_function = {
    "name": "report_compliance_bugs",
    "description": "reports compliance bugs in the code",
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
                            "description": "the type of bug, e.g. 'privacy-leak', using standard bug types from the MITRE CWE taxonomy"
                        },
                        "description": {
                            "type": "string",
                            "description": "a description in markdown format of why the bug is a bug and how it might be exploited",
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


class ComplianceFunctionProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'compliance-function.prompt',
            'role_system': 'compliance-function-role-system.prompt'
        }, {'model': OpenAIDefaults.boost_default_gpt_model,
            'temperature': OpenAIDefaults.temperature_terse_and_accurate,
            'functions': [report_bug_function],
            'function_call': {"name": "report_compliance_bugs"}})

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 80% of the buffer for the input, and 20% for the output, since the function call outputs are small
        # and we're much terser in output in this processor
        return math.floor(total_max * 0.8)

    def compliance_code(self, data, account, function_name, correlation_id):

        # Extract the code from the json data
        code = data[self.get_chunkable_input()]

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code})

        # if result['messages'] has a field 'function_call', then we have the data for a function call

        if 'function_call' in result['results'][0]['message']:
            # if we get here, we have a function call in the results array.  loop through each of the results and add the array of arguments to the bugs array
            # result['results'][0]['message']['function_call']['arguments'] is a JSON formatted string. parse it into a JSON object.  it may be corrupt, so ignore
            # any errors
            bugs = []
            for r in result['results']:
                try:
                    json_bugs = json.loads(r['message']['function_call']['arguments'])
                    bugs.extend(json_bugs["bugs"])
                except Exception:
                    pass

            return {
                "status": "bugsfound",
                "details": bugs
            }
        else:
            return {
                "status": "nobugsfound",
                "details": []
            }
