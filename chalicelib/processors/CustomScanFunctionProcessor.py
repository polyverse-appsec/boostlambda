from chalicelib.processors.BugFunctionGenericProcessor import BugFunctionGenericProcessor
from chalicelib.version import API_VERSION
from chalice import BadRequestError


class CustomScanFunctionProcessor(BugFunctionGenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         'customscan-function.prompt',
                         'customscan-function-role-system.prompt',
                         'customScan',
                         'the type of issue')

    # enable injection of the categories into the function schema
    def initialize_from_data(self, log, data, account, function_name, correlation_id, prompt_format_args, params):
        if 'scanTypeDescription' in data:
            params['functions'][0]['parameters']['properties']['bugs']['items']['properties']['bugType']['description'] = \
                data['scanTypeDescription']

        return super().initialize_from_data(
            log, data, account, function_name, correlation_id, prompt_format_args, params)

    def collect_inputs_for_processing(self, data):
        prompt_format_args = super().collect_inputs_for_processing(data)

        prompt_format_args['customScanGuidance'] = data['customScanGuidance']
        prompt_format_args['customScanCategories'] = data['customScanCategories']

        return prompt_format_args

    def custom_scan(self, data, account, function_name, correlation_id):
        # Extract the prompt from the json data
        customScanGuidance = data['customScanGuidance'] if 'customScanGuidance' in data else None
        if customScanGuidance is None:
            raise BadRequestError("Error: please provide custom scan guidance to run against the code fragment")

        # Extract the categories from the json data
        customScanCategories = data['customScanCategories'] if 'customScanCategories' in data else None
        if customScanCategories is None:
            raise BadRequestError("Error: please provide custom scan categories to run against the code fragment")

        scanTypeDescription = data['scanTypeDescription'] if 'scanTypeDescription' in data else None
        if scanTypeDescription is None:
            data['scanTypeDescription'] = \
                f"the type of code logic issue, using one of the following types: {customScanCategories}"

        # my_function_schema['parameters']['properties']['bugs']['items']['properties']['bugType']['description'] = \
        # scanTypeDescription

        return self.process_input_with_function_output(data, account, function_name, correlation_id)
