from chalice.test import Client
from app import app
import json

from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


# load the data files into a string, relative to the root directory
with open('./tests/data/chat/blueprint.json', 'r') as file:
    blueprint_json = file.read()
    blueprint = json.loads(blueprint_json).get('data')


def test_chat():
    with Client(app) as client:
        request_body = {
            'query': 'What is this project?',
            'summaries': ['system', [blueprint]],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("unknown" in result['analysis'].lower()) or ("javascript" in result['analysis'].lower())
        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_chat_with_code():
    with Client(app) as client:
        request_body = {
            'code': 'int main() {\n\tprintf("Hello world!");\n\treturn 0;\n}',
            'query': 'What is this code language?',
            'summaries': ['system', [blueprint]],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("C" in result['analysis'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'
