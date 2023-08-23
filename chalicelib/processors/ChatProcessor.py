from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults

import math


class ChatProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'chat.prompt'],
            ['system', 'chat-role-system.prompt']],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
             'temperature': OpenAIDefaults.temperature_medium_with_explanation},
            AnalysisOutputFormat.prose, [
                AnalysisOutputFormat.bulletedList,
                AnalysisOutputFormat.rankedList,
                AnalysisOutputFormat.numberedList])

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and 10% for the output
        return math.floor(total_max * 0.8)

    def process_chat(self, data, account, function_name, correlation_id):
        # Code is optional and may not be present
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        # if we're injecting code into the prompts, then we need to format it with surrounding code blocks
        if code is not None:
            formatted_code = f':\n\n```\n{code}```'

        # Extract the query from the json data - we need a query to run no matter what
        query = data['query'] if 'query' in data else None
        if query is None:
            raise BadRequestError("Error: please provide a custom query to run against the data")

        prompt_format_args = {
            self.get_chunkable_input(): formatted_code, 'query': query
        } if code is not None else {'query': query}

        result = self.process_input(data, account, function_name, correlation_id,
                                    prompt_format_args)

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
