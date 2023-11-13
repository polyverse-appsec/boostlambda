from chalice.test import Client
from app import app
import json

with open('./tests/data/performance/hadoop_commitBlockSynchronization.java', 'r') as file:
    hello_world_java = file.read()

from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


def test_generate_tests_function():
    with Client(app) as client:

        request_body = {
            'code': hello_world_java,
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version,
        }

        response = client.lambda_.invoke(
            'generate_tests', request_body)

        assert response.payload['statusCode'] == 200

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'testFramework' in details
        assert 'junit' in details['testFramework'].lower()

        assert 'testProgrammingLanguage' in details
        assert 'java' in details['testProgrammingLanguage'].lower()

        assert 'recommendedTestLanguageFileExtension' in details
        assert 'java' in details['recommendedTestLanguageFileExtension']

        assert 'generatedTestCases' in details
        assert len(details['generatedTestCases']) > 0
        for test in details['generatedTestCases']:
            assert 'sourceCode' in test
            print(test['sourceCode'])

            assert 'testType' in test
            print(test['testType'])

            assert 'testFileName' in test
            print(test['testFileName'])


""" {
    "testFramework": "junit",
    "testProgrammingLanguage": "java",
    "recommendedTestLanguageFileExtension": "java",
    "generatedTestCases": [
        {
            "sourceCode": "public class HelloWorldTest {\n    @Test\n    public void testHelloWorld() {\n        HelloWorld.main(new String[0]);\n    }\n}\n",
            "testType": "unit",
            "testFileName": "testHelloWorld.java"
        }
    ]
}
"""


def test_generate_tests_function_language_framework():
    with Client(app) as client:

        request_body = {
            'code': hello_world_java,
            'testFramework': 'pytest',
            'testType': 'unit',
            'language': 'python',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version,
        }

        response = client.lambda_.invoke(
            'generate_tests', request_body)

        assert response.payload['statusCode'] == 200

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'testFramework' in details
        assert 'pytest' in details['testFramework']

        assert 'testProgrammingLanguage' in details
        assert 'python' in details['testProgrammingLanguage']

        assert 'recommendedTestLanguageFileExtension' in details
        assert 'py' in details['recommendedTestLanguageFileExtension']

        assert 'generatedTestCases' in details
        assert len(details['generatedTestCases']) > 0
        for test in details['generatedTestCases']:
            assert 'sourceCode' in test
            print(test['sourceCode'])

            assert 'testType' in test
            print(test['testType'])

            assert 'testFileName' in test
            print(test['testFileName'])
