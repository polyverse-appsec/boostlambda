from chalicelib.processors.FunctionGenericProcessor import FunctionGenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults, num_tokens_from_string

import math

chat_driver = {
    "name": "chat_driver",
    "description": "The API that will determine what kind of chat request has been made",
    "parameters": {
        "type": "object",
        "properties": {
            "chatAction": {
                "type": "string",
                "description": ("The kind of Chat operation being made by the user:"
                                "Options include:\n"
                                "* searchProjectWideAnalysis - Search or ask a question about the project-wide analysis and analysis summaries.\n"
                                "* searchAnalysisOfASoureFile - Search or ask a question about the code analysis for a specific source file\n"
                                "* getHelpWithProductUsageOrDocumentation - Ask a question about how to use the product or search the product documentation.\n"
                                "* performUIOperation - Execute a UI operation, like show UI tab, press an analysis button, or configure a feature\n"
                                "* unsupportedOperation - Unsupported operation that doesn't match any other option, is an invalid user request, or isn't a high-confidence command match"),
                "enum": [
                    # search project analysis
                    "searchProjectWideAnalysis",

                    # search file analysis
                    "searchAnalysisOfASoureFile",

                    # get help with product usage or documentation
                    "getHelpWithProductUsageOrDocumentation",

                    # performUIOperation
                    "performUIOperation",

                    # unknown operation by user or unsupported by product
                    "unsupportedOperation"
                ]
            },
            "includeSecurityAnalysisInfoForSearchContext": {
                "type": "boolean",
                "description": ("If true, include security analysis information for the search context. "
                                "If false, do not include security analysis information for the search context. "
                                "If not specified, the default is false.")
            },
            "includeComplianceAnalysisInfoForSearchContext": {
                "type": "boolean",
                "description": ("If true, include compliance analysis information for the search context. "
                                "If false, do not include compliance analysis information for the search context. "
                                "If not specified, the default is false.")
            },
            "targetSourceFiles": {
                "type": "array",
                "description": ("The list of source files to search for analysis results. "
                                "If not specified, the default is the current file or project."),
                "items": {
                    "type": "string",
                    "description": ("A source file to search for analysis results.")
                }
            },
        }
    }
}


class ChatDriverFunctionProcessor(FunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'chat-driver-function.prompt'],
                          ['system', 'chat-driver-function-role-system.prompt']],
                         'chat_driver',
                         chat_driver,
                         {'model': OpenAIDefaults.boost_model_gpt35_cheap_chat,
                          'temperature': OpenAIDefaults.temperature_terse_and_accurate})

    def get_default_max_tokens(self):
        return 1000

    def calculate_input_token_buffer(self, total_max) -> int:
        # our user input is tiny, but with the max tokens reduced significantly
        #     the system messages need buffer space, and the function
        #     definition needs space as well
        # the system message in particular can contain the filelist, which can be large
        return math.floor(total_max * 0.75)

    def calculate_system_message_token_buffer(self, total_max) -> int:
        return math.floor(total_max * 0.25)

    def get_function_definition(self):
        return chat_driver

    # this is a simple quick chat driver... we want tiny inputs, no chunking
    def get_chunkable_input(self) -> str:
        return None

    filelist_prompt = "The list of files in the project are:\n```\n{filelist}\n```"

    def collect_inputs_for_processing(self, data):
        # Extract the chat request from the json data
        userRequest = data.get('userRequest') if 'userRequest' in data else None
        if userRequest is None:
            raise BadRequestError("Error: please provide the user request")

        filelist = data.get('filelist') if 'filelist' in data else None
        if filelist is not None:
            if not isinstance(filelist, list) or not all(isinstance(elem, str) for elem in filelist):
                raise BadRequestError("Error: filelist must be a list of strings")

            # convert filelist from a list of strings to a single string with newline delimited filenames
            # note we prepend with the count of files, since we are likely to truncate large lists of files
            filelist = f"{str(len(filelist))} Files\n\n   " + "\n   ".join(filelist)
            filelist = self.filelist_prompt.format(filelist=filelist)
        extra_tokens = num_tokens_from_string(filelist)[0] if filelist is not None else 0

        # set a very small token max since we're only translating a short user request into a subsequent user request
        data['max_tokens'] = self.get_default_max_tokens() + extra_tokens

        default_format_args = {'userRequest': userRequest}
        if filelist is not None:
            default_format_args['filelist'] = filelist

        return default_format_args

    def chat_driver(self, data, account, function_name, correlation_id):
        return self.process_input_with_function_output(data, account, function_name, correlation_id)
