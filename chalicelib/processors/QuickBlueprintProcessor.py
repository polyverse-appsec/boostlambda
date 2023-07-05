from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError

import math


class QuickBlueprintProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['system', 'quick-blueprint-role-system.prompt'],
                          ['system', 'quick-blueprint-projectfile-role-system.prompt'],
                          ['main', 'quick-blueprint.prompt']
                          ],
                         [['response', 'quick-blueprint']],
                         {'model': OpenAIDefaults.boost_default_gpt_model,
                          'temperature': OpenAIDefaults.temperature_terse_and_accurate},
                         AnalysisOutputFormat.prose)

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and 10% for the output
        return math.floor(total_max * 0.9)

    def get_chunkable_input(self) -> str:
        return 'code'

    def blueprint_code(self, data, account, function_name, correlation_id):
        filelist = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if filelist is None:
            raise BadRequestError("Error: please provide the filelist")

        projectFile = data['projectFile'] if 'projectFile' in data else None
        if projectFile is None:
            raise BadRequestError("Error: please provide the projectFile")

        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide the sample code")

        draftBlueprint = data['draftBlueprint'] if 'draftBlueprint' in data else None
        if draftBlueprint is None:
            raise BadRequestError("Error: please provide the draftBlueprint")

        projectName = data['projectName'] if 'projectName' in data else None
        if projectName is None:
            raise BadRequestError("Error: please provide the projectName")

        result = self.process_input(data, account, function_name, correlation_id,
                                    {'filelist': filelist,
                                     'projectFile': projectFile,
                                     'code': code,
                                     'draftBlueprint': draftBlueprint,
                                     'projectName': projectName})

        return {
            "blueprint": result['output'],
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }
