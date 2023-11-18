from chalice.test import Client
from app import app
import json

with open('./tests/data/convert/HelloWorld.java', 'r') as file:
    hello_world_java = file.read()

from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


def test_convert_code_function():
    with Client(app) as client:

        output_language = 'python'  # Replace this with the desired output language
        request_body = {
            'explanation': 'This is a simple program that prints "Hello, World!" to the console.',
            'code': hello_world_java,
            'originalFilename': 'HelloWorld.java',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version,
            'targetLanguage': output_language
        }
        response = client.lambda_.invoke(
            'convert_code', request_body)

        assert response.payload['statusCode'] == 200

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'convertedCode' in details
        assert 'print("Hello, World!")' in details['convertedCode'] or 'print(\'Hello, World!\')' in details['convertedCode']

        assert 'issuesDuringConversion' in details
        assert len(details['issuesDuringConversion']) == 0

        assert 'convertedFileExtension' in details
        assert details['convertedFileExtension'] == 'py'

        assert 'recommendedConvertedFilenameBase' in details
        assert details['recommendedConvertedFilenameBase'] == 'hello_world'
