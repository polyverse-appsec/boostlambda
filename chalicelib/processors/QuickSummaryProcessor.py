from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError

import math


class QuickSummaryProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['system', 'quick-summary-role-system.prompt'],
                          ['system', 'quick-summary-files-system.prompt'],
                          ['system', 'quick-summary-categorization-system.prompt'],
                          ['system', 'quick-summary-examples-system.prompt'],
                          ['main', 'quick-summary-user.prompt']
                          ],
                         None,
                         {'model': OpenAIDefaults.boost_default_gpt_model,
                          'temperature': OpenAIDefaults.temperature_terse_and_accurate},
                         AnalysisOutputFormat.prose)

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 85% of the buffer for the input, and 10% for the output
        return math.floor(total_max * 0.85)

    # disable chunking... the input should not be very big, since there is essentially
    #     no user input in the prompt. This is a safety guard
    #     the only user input is in the guidelines, and we don't want to chunk that
    #     we'll just truncate it if needed
    def get_chunkable_input(self) -> str:
        return ''

    # we're going to use 80% of our input buffer for system messages (e.g. background info)
    #    since the majority of the input will be context data in system prompts
    def calculate_system_message_token_buffer(self, total_max) -> int:
        return math.floor(self.calculate_input_token_buffer(total_max) * 0.80)

    def quick_summary(self, data, account, function_name, correlation_id):
        filelist = data['filelist'] if 'filelist' in data else None
        if filelist is None:
            raise BadRequestError("Error: please provide the filelist")
        else:
            if not isinstance(filelist, list) or not all(isinstance(elem, str) for elem in filelist):
                raise BadRequestError("Error: filelist must be a list of strings")

        # convert filelist from a list of strings to a single string with newline delimited filenames
        # note we prepend with the count of files, since we are likely to truncate large lists of files
        filelist = f"{str(len(filelist))} Files\n\n   " + "\n   ".join(filelist)

        issue_categorization = data['issue_categorization'] if 'issue_categorization' in data else None
        if issue_categorization is None:
            raise BadRequestError("Error: please provide the issue_categorization")

        examples = data['examples'] if 'examples' in data else None
        if examples is None:
            raise BadRequestError("Error: please provide the examples")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {'filelist': filelist,
                                     'issue_categorization': issue_categorization,
                                     'examples': examples})

        return {
            "summary": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
