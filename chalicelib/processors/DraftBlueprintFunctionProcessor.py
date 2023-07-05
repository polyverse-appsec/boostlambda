from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION

import json


draft_blueprint_function = {
    "name": "build_draft_blueprint",
    "description": "The API that will build a draft Architectural Blueprint Summary based on a filelist, recommend a representative source file and identify the main project build/package description file",
    "parameters": {
        "draftBlueprint": {
            "type": "string",
            "description": "The Architectural Blueprint Summary that was drafted"
        },
        "recommendedSampleSourceFile": {
            "type": "string",
            "description": "The sample source file that most represents the type of development principles being used"
        },
        "recommendedProjectDeploymentFile": {
            "type": "string",
            "description": "The project build or deployment file that describes how the project code is built and deployed"
        },
    }
}


class DraftBlueprintFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'draft-blueprint-function.prompt',
                         'draft-blueprint-function-role-system.prompt',
                         'draft-blueprint',
                         draft_blueprint_function)

    # default is capturing bugs in the function output
    def process_function_output(self, result, log):

        arguments = {}
        # if we get here, we have a function call in the results array.  loop through each of the results and add the array of arguments to the bugs array
        # result['results'][0]['message']['function_call']['arguments'] is a JSON formatted string. parse it into a JSON object.  it may be corrupt, so ignore
        # any errors
        for r in result['results']:
            try:
                json_arguments = json.loads(r['message']['function_call']['arguments'])
                arguments["draftBlueprint"] = json_arguments["draftBlueprint"]
                arguments["recommendedSampleSourceFile"] = json_arguments["recommendedSampleSourceFile"]
                arguments["recommendedProjectDeploymentFile"] = json_arguments["recommendedSampleSourceFile"]

            except Exception as e:
                log(f"Error parsing function call arguments: {e}")
                pass

        success = 1
        if len(result['results']) == 0:
            log("No results returned from function call")
            success = 0

        if "draftBlueprint" not in arguments:
            log("draftBlueprint was not generated")
            success = 0

        if "recommendedSampleSourceFile" not in arguments:
            log("sample source file not identified")
            success = 0

        if "recommendedProjectDeploymentFile" not in arguments:
            log("Project File not identified")
            success = 0

        return {
            "status": str(success),
            "details": arguments
        }

    def draft_blueprint(self, data, account, function_name, correlation_id):
        return self.check_code_with_function(data, account, function_name, correlation_id)
