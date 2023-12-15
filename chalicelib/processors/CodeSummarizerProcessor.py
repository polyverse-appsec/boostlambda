from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError


class CodeSummarizerProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'codesummarizer.prompt']],
            None,
            {'model': OpenAIDefaults.boost_model_gpt35_cheap_chat,
             'temperature': OpenAIDefaults.temperature_terse_and_accurate},
            AnalysisOutputFormat.prose)

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_output_token_buffer(self, data, input_buffer_size, output_buffer_size, total_max, enforce_max=True) -> int:
        return 500

    def summarize_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        result = self.process_input(data, account, function_name, correlation_id, {self.get_chunkable_input(): code})

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
