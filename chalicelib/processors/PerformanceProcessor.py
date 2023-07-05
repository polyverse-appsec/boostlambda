from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError


class PerformanceProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'performance.prompt'],
            ['system', 'performance-role-system.prompt']],
            None,
            {'model': OpenAIDefaults.boost_default_gpt_model,
             'temperature': OpenAIDefaults.temperature_medium_with_explanation},
            AnalysisOutputFormat.rankedList, [AnalysisOutputFormat.bulletedList, AnalysisOutputFormat.rankedList, AnalysisOutputFormat.numberedList])

    def get_chunkable_input(self) -> str:
        return 'code'

    def check_performance(self, data, account, function_name, correlation_id):

        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        result = self.process_input(data, account, function_name, correlation_id, {self.get_chunkable_input(): code})

        return {
            "analysis": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
