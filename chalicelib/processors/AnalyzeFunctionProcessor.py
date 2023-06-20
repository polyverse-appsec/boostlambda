from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError


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

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code})

        #if result['messages'] has a field 'function_call', then we have the data for a function call

        if 'function_call' in result['results'][0]['message']:
            return {
                "status": "bugsfound",
                "analysis": result['results'][0]['message']['function_call']['arguments']
            } 
        else:
            return {
                "status": "nobugsfound",
            }
        
