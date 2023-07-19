from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError

import json
import math


build_draft_blueprint = {
    "name": "build_draft_blueprint",
    "description": "The API that will build a draft Architectural Blueprint Summary based on a filelist, recommend a representative source file and identify the main project build/package description file",
    "parameters": {
        "type": "object",
        "properties": {
            "draftBlueprint": {
                "type": "string",
                "description": "The Architectural Blueprint Summary that was drafted"
            },
            "recommendedListOfFilesToExcludeFromAnalysis": {
                "type": "array",
                "description": "List of project folders and files to exclude from project analysis that do not likely contain any useful source, build or project information.",
                "items": {
                    "type": "string",
                    "description": "Each folder or file that should be excluded from software project analysis."
                }
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
}


class DraftBlueprintFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'draft-blueprint-function.prompt',
                         'draft-blueprint-function-role-system.prompt',
                         'build_draft_blueprint',
                         build_draft_blueprint)

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and the last 10% for the generated blueprint
        return math.floor(total_max * 0.9)

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
                arguments["recommendedSampleSourceFile"] = json_arguments["recommendedSampleSourceFile"] if "recommendedSampleSourceFile" in json_arguments else ""
                arguments["recommendedProjectDeploymentFile"] = json_arguments["recommendedProjectDeploymentFile"] if "recommendedProjectDeploymentFile" in json_arguments else ""
                arguments["recommendedListOfFilesToExcludeFromAnalysis"] = json_arguments["recommendedListOfFilesToExcludeFromAnalysis"] if "recommendedListOfFilesToExcludeFromAnalysis" in json_arguments else []

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

        if "recommendedListOfFilesToExcludeFromAnalysis" not in arguments:
            log("recommendedListOfFilesToExcludeFromAnalysis was not generated")
            success = 0

        if "recommendedSampleSourceFile" not in arguments:
            log("sample source file not identified")
            success = 0

        if "recommendedProjectDeploymentFile" not in arguments:
            log("Project File not identified")
            success = 0

        return {
            "status": success,
            "details": arguments
        }

    def get_chunkable_input(self) -> str:
        return "filelist"

    def collect_inputs_for_processing(self, data):
        # Extract the fileList from the json data
        filelist = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if filelist is None:
            raise BadRequestError("Error: Please provide a filelist to build draft blueprint")
        else:
            if not isinstance(filelist, list) or not all(isinstance(elem, str) for elem in filelist):
                raise BadRequestError("Error: filelist must be a list of strings")

        # convert filelist from a list of strings to a single string with newline delimited filenames
        filelist = "\n".join(filelist)

        # Extract the projectName from the json data
        projectName = data['projectName'] if 'projectName' in data else None
        if projectName is None:
            raise BadRequestError("Error: please provide a projectName to build draft blueprint")

        prompt_format_args = {self.get_chunkable_input(): filelist,
                              "projectName": projectName}

        if 'inputMetadata' in data:
            inputMetadata = json.loads(data['inputMetadata'])
            lineNumberBase = inputMetadata['lineNumberBase']
            prompt_format_args['lineNumberBase'] = f"When identifying source numbers for issues," \
                                                   f" treat the first line of the code as line number {lineNumberBase + 1}"

        return prompt_format_args

    def draft_blueprint(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
