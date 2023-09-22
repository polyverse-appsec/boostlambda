from chalicelib.processors.CustomProcessor import CustomProcessor
from chalicelib.app_utils import process_request
from chalice.test import Client
import json
from chalice import Chalice

from .test_version import client_version

app = Chalice(app_name='boost')


class TruncationTestProcessor(CustomProcessor):

    def calculate_input_token_buffer(self, total_max) -> int:
        return 100

    def get_chunkable_input(self) -> str:
        return ''


truncateProcessor = TruncationTestProcessor()


@app.lambda_function(name='truncatecustomprocess')
def customprocess(event, _):
    return process_request(event, truncateProcessor.customprocess_code, truncateProcessor.api_version)


def test_truncated_messages():
    with Client(app) as client:
        def truncated_data(size):
            return ' '.join([f'word{i}' for i in range(1, size + 1)])

        prompt = "Count the words in the following.\n\n\n"
        this_role_system = "I am a word counter."
        request_body = {
            'messages': json.dumps([
                {
                    "role": "system",
                    "content": this_role_system
                },
                {
                    "role": "user",
                    "content": prompt + truncated_data(50)
                },
                {
                    "role": "user",
                    "content": truncated_data(20)
                },
                {
                    "role": "user",
                    "content": truncated_data(200)
                }
            ]),
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'truncatecustomprocess', request_body)

        assert response.payload['statusCode'] == 200

        result = json.loads(response.payload['body'])

        assert "Truncated input" in result['analysis']
        assert "discarded ~461 " in result['analysis']
        assert " 46" in result['analysis']
