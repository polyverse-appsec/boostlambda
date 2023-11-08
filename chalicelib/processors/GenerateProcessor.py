from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalice import BadRequestError
from chalicelib.usage import OpenAIDefaults


class GenerateProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'convert.prompt'],
                          ['system', 'convert-role-system.prompt'],
                          ['assistant', 'convert-role-assistant.prompt'],
                          ['user', 'convert-role-user.prompt']],
                         None,
                         {'model': OpenAIDefaults.boost_default_gpt_model,
                          'temperature': OpenAIDefaults.temperature_medium_with_explanation},
                         AnalysisOutputFormat.prose)

    # we are going to chunk the explanation, since its bigger than the code presumptively
    # However - realistically, we should be chunking both. But they segment independently - e.g.
    # 1 line of code could be a paragraph of explanation. Harder to slice and dice them blindly
    # into coordinated chunks. But there's a good chance chunking one or the other only will break
    # both the conversion and ability to chunk (e.g. if the code is over the buffer size, and we chunk
    # only the explanation, we'll never be able to process the code, and vice versa)
    def get_chunkable_input(self) -> str:
        return 'explanation'

    def convert_code(self, data, account, function_name, correlation_id):
        # Extract the explanation and original_code from the json data
        explanation = data.get(self.get_chunkable_input())
        if explanation is None:
            raise BadRequestError("Error: please provide the initial code explanation")

        # old client version compatibility shim (can be removed once all clients upgraded to 1.0.1 or better)
        if 'originalCode' in data:
            data['code'] = data['originalCode']

        code = data.get('code') if 'code' in data else None
        if code is None:
            raise BadRequestError("Error: please provide the original code")

        # The output language is optional; if not set, then default to existing language
        outputlanguage = data.get('language', 'programming')

        result = self.process_input(data, account, function_name, correlation_id,
                                    {self.get_chunkable_input(): explanation,
                                     'code': code,
                                     'language': outputlanguage})

        return {
            "code": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
