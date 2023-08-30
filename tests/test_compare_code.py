from chalice.test import Client
from app import app
import json

# load the first codebase into a string, relative to the root directory
with open('./tests/data/comparison/sync_urls.sh', 'r') as file:
    sync_urls_sh = file.read()

# load the first comparand codebase into a string, relative to the root directory
with open('./tests/data/comparison/sync_urls.py', 'r') as file:
    sync_urls_py = file.read()

# load the second comparand codebase into a string, relative to the root directory
with open('./tests/data/comparison/sync_urls_2.py', 'r') as file:
    sync_urls_2_py = file.read()

from test_version import client_version


def test_compare_code():
    with Client(app) as client:
        request_body = {
            'code': sync_urls_sh,
            'code_compare': sync_urls_py,
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'compare_code', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])

        assert analysis['analysis'] != ''

        assert 'auth-type' in analysis['analysis']

        request_body['compare_code'] = sync_urls_2_py

        response = client.lambda_.invoke(
            'compare_code', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])

        assert analysis['analysis'] != ''

        assert 'add_permission' in analysis['analysis']

        # we should be detecting changes in the monitors handling and also the command line arguments, but these
        #    aren't being detected yet
        # assert 'monitors' in analysis['analysis']
        # assert 'arguments' in analysis['analysis']

        request_body['code'] = sync_urls_py

        response = client.lambda_.invoke(
            'compare_code', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])

        assert analysis['analysis'] != ''

        # isn't picking up major differences, other than changes in the main and functions
        assert 'function' in analysis['analysis']
