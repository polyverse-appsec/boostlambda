from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults


class TestGeneratorProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'testgen.prompt'],
                          ['system', 'testgen-role-system.prompt']],
                         None,
                         {'model': OpenAIDefaults.boost_default_gpt_model,
                          'temperature': OpenAIDefaults.temperature_medium_with_explanation})

    def get_chunkable_input(self) -> str:
        return 'code'

    def testgen_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()]

        language = data['language']
        outputlanguage = language
        if outputlanguage is None:
            outputlanguage = "python"

        framework = data['framework']
        if framework is None:
            if outputlanguage == "python":
                framework = "pytest"
            else:
                framework = "the best framework for " + outputlanguage + " tests"

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): code,
                                     'language': outputlanguage,
                                     'framework': framework})

        return {
            "testcode": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
