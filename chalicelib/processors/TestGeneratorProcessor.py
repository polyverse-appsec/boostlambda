from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError


class TestGeneratorProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'testgen.prompt'],
                          ['system', 'testgen-role-system.prompt']],
                         None,
                         {'model': OpenAIDefaults.boost_default_gpt_model,
                          'temperature': OpenAIDefaults.temperature_medium_with_explanation},
                         AnalysisOutputFormat.prose)

    def get_chunkable_input(self) -> str:
        return 'code'

    def testgen_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide the code to test")

        outputlanguage = data['language'] if 'language' in data else None
        if outputlanguage is None:
            outputlanguage = "language of this code"

        framework = data['framework'] if 'framework' in data else None
        if framework is None:
            if outputlanguage == "python":
                framework = "pytest"
            else:
                framework = "the best matched framework"

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code,
                                     'language': outputlanguage,
                                     'framework': framework})

        return {
            "testcode": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
