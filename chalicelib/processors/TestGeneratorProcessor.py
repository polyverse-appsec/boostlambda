from chalicelib.processors.GenericProcessor import GenericProcessor
from chalicelib.version import API_VERSION


class TestGeneratorProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'testgen.prompt',
            'role_system': 'testgen-role-system.prompt'
        })

    def testgen_code(self, data, account, function_name, correlation_id):
        original_code = data['code']

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
                                    {'original_code': original_code,
                                     'language': outputlanguage,
                                     'framework': framework})

        return {"testcode": result['output']}
