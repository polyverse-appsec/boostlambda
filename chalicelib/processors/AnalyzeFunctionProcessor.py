from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError
import json


report_bug_function_old = {
    "name": "report_security_bugs",
    "description": "reports security bugs in the code",
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
                            "description": "the type of bug, e.g. 'sql-injection', using standard bug types from the MITRE CWE taxonomy"
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
    "name": "report_security_bugs",
    "description": "reports security bugs in the code",
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
                            "description": "the type of bug, e.g. 'sql-injection', using standard bug types from the MITRE CWE taxonomy"
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

class AnalyzeFunctionProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'analyze-function.prompt',
            'role_system': 'analyze-function-role-system.prompt'
        })
        self.functions = [report_bug_function]
        self.function_call = {"name": "report_security_bugs"}
        self.max_tokens = 8100

    def get_chunkable_input(self) -> str:
        return 'code'

    def analyze_code(self, data, account, function_name, correlation_id):

        # Extract the code from the json data
        code = data[self.get_chunkable_input()]

        # unless the temperature is explicity set in data, set it to .2
        if 'temperature' not in data:
            data['temperature'] = 0.1

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code})

        #if result['messages'] has a field 'function_call', then we have the data for a function call

        if 'function_call' in result['results'][0]['message']:
            #if we get here, we have a function call in the results array.  loop through each of the results and add the array of arguments to the bugs array
            #result['results'][0]['message']['function_call']['arguments'] is a JSON formatted string. parse it into a JSON object.  it may be corrupt, so ignore
            #any errors
            bugs = []
            for r in result['results']:
                try:
                    json_bugs = json.loads(r['message']['function_call']['arguments'])
                    bugs.extend(json_bugs["bugs"])
                except:
                    pass

            return {
                "status": "bugsfound",
                "analysis": bugs
            } 
        else:
            return {
                "status": "nobugsfound",
                "analysis": []
            }
        
