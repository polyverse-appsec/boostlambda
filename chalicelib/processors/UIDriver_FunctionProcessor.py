from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import math

ui_driver = {
    "name": "ui_driver",
    "description": "The API that will determine what UI operation to execute",
    "parameters": {
        "type": "object",
        "properties": {
            "uiAction": {
                "type": "string",
                "description": ("The UI action to take based on the user request:"
                                "Options include:\n"
                                "* startAnalysisOfProject - Start a long-running analysis of the project with configured analyis types\n"
                                "* askForProductHelp - Ask for product help, search the documentation, or view instructions\n"
                                "* showProjectSummaryOrOverallStatus - Show a long-form read-only text summary of the current project architecture\n"
                                "* showComplianceSummaryOrStatus -Show long-form read-only text summary of the current project compliance status\n"
                                "* showSecuritySummaryOrStatus - Show long-form read-only text summary of the current project security status\n"
                                "* enableSecurityAnalysis - Enable security analysis for the project\n"
                                "* disableSecurityAnalysis - Disable security analysis for the project\n"
                                "* enableComplianceAnalysis - Enable compliance analysis for the project\n"
                                "* disableComplianceAnalysis - Disable compliance analysis for the project\n"
                                "* enableDocumentationGeneration - Enable documentation generation for the project\n"
                                "* disableDocumentationGeneration - Disable documentation generation for the project\n"
                                "* unsupportedOperation - Unsupported operation that doesn't match any other option, is an invalid user request, or isn't a high-confidence command match"),
                "enum": [
                    # run analysis
                    "startAnalysisOfProject",

                    # ask for help
                    "askForProductHelp",

                    # show analysis summaries of project
                    "showProjectSummaryOrOverallStatus",
                    "showSecuritySummaryOrStatus",
                    "showComplianceSummaryOrStatus"

                    # toggle analysis types
                    "enableSecurityAnalysis",
                    "disableSecurityAnalysis",

                    "enableComplianceAnalysis",
                    "disableComplianceAnalysis",

                    "enableDocumentationGeneration",
                    "disableDocumentationGeneration",

                    # unknown operation by user or unsupported by product
                    "unsupportedOperation"
                ]
            },
        }
    }
}


class UIDriverFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'ui-driver-function.prompt'],
                          ['system', 'ui-driver-function-role-system.prompt']],
                         'ui_driver',
                         ui_driver,
                         {'model': OpenAIDefaults.boost_model_gpt35_cheap_chat,
                          'temperature': OpenAIDefaults.temperature_terse_and_accurate})

    def get_default_max_tokens(self, data=None):
        return min(1000, super().get_default_max_tokens(data))

    def calculate_input_token_buffer(self, total_max) -> int:
        # our user input is tiny, but with the max tokens reduced significantly
        #     the system messages need buffer space, and the function
        #     definition needs space as well
        return math.floor(total_max * 0.75)

    def calculate_system_message_token_buffer(self, total_max) -> int:
        return math.floor(total_max * 0.25)

    def get_function_definition(self):
        return ui_driver

    # this is a simple quick UI driver... we want tiny inputs
    def get_chunkable_input(self) -> str:
        return None

    def collect_inputs_for_processing(self, data):
        # Extract the user command from the json data
        userCommand = data.get('userCommand') if 'userCommand' in data else None
        if userCommand is None:
            raise BadRequestError("Error: please provide the user command request")

        # set a small token max since we're only translating a short user request into a UI command
        data['max_tokens'] = self.get_default_max_tokens(data)

        return {'userCommand': userCommand}

    def ui_driver(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
