from chalice.test import Client
from app import app
import json
from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


def test_explain():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_explain_with_guideline():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'guidelines': ['system',
                           ['This application code should be able to print "Hello, Cruel World!" to the console.',
                            'This application code should be written in TypeScript or JavaScript.']],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_generate_outputlanguage():
    with Client(app) as client:
        output_language = 'python'  # Replace this with the desired output language
        request_body = {
            'explanation': 'This is a simple program that prints "Hello, World!" to the console.',
            'code': 'public class HelloWorld {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version,
            'output_language': output_language
        }
        response = client.lambda_.invoke(
            'generate', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        conversion = json.loads(response.payload['body'])
        assert 'print("Hello, World!")' in conversion['code'] or 'print(\'Hello, World!\')' in conversion['code']


# test the authentication with the session parameter
def test_auth():
    with Client(app) as client:
        request_body = {
            'session': 'testemail: foo@bar.com',
            'code': 'print("Hello, World!")',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 401

        # now test with an email of alexgo@gmail.com
        request_body = {
            'session': 'testemail: alexgo@gmail.com',
            'code': 'print("Hello, World!")',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 401

        # now test with an email of jkthecjer@gmail.com
        request_body = {
            'session': 'testemail: jkthecjer@polytest.ai',
            'code': 'print("Hello, World!")',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200

        # now test with an email of unittest@polytest.ai
        request_body = {
            'session': 'testemail: unittest@polytest.ai',
            'code': 'print("Hello, World!")',
            'organization': 'polytest.ai',
            'version': client_version
        }
        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200


def test_testgen():
    with Client(app) as client:

        request_body = {
            'language': 'python',
            'framework': 'pytest',
            'code': 'print("Hello, World!")',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }
        response = client.lambda_.invoke(
            'testgen', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_analyze():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'analyze', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_compliance():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'compliance', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_codeguidelines():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'codeguidelines', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_blueprint():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'guidelines': ['system',
                           ['This application code should be able to print "Hello, Cruel World!" to the console.',
                            'This application code should be written in TypeScript or JavaScript.']],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'codeguidelines', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_customprocess_prompt():
    with Client(app) as client:
        code = 'print("Hello, World!")'
        prompt = "Analyze this code to identify use of code incompatible with a commercial license, such as any open source license.\n\nExamples of licenses include BSD, MIT, GPL, LGPL, Apache or other licenses that may conflict with commercial licenses.\n\nFor any identified licenses in the code, provide online web links to relevant license analysis.\n\n\n" + code
        request_body = {
            'code': code,
            'prompt': prompt,
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'customprocess', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_customprocess_messages():
    with Client(app) as client:
        code = 'print("Hello, World!")'
        prompt = "Analyze this code to identify use of code incompatible with a commercial license, such as any open source license.\n\nExamples of licenses include BSD, MIT, GPL, LGPL, Apache or other licenses that may conflict with commercial licenses.\n\nFor any identified licenses in the code, provide online web links to relevant license analysis.\n\n\n" + code
        this_role_system = "I am a software architect bot. I will analyze the code for architectural, algorithmic and design issues."
        request_body = {
            'messages': json.dumps([
                {
                    "role": "system",
                    "content": this_role_system
                },
                {
                    "role": "user",
                    "content": prompt
                }]),
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'customprocess', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_summary_inputs():
    with Client(app) as client:
        request_body = {
            'inputs': 'first sentence\nsecond sentence\nthird sentence',
            'analysis_label': 'Explanation',
            'analysis_type': 'explain',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'summarize', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")


def test_summary_chunks():
    with Client(app) as client:
        request_body = {
            'chunk_0': 'first sentence',
            'chunk_1': 'second sentence',
            'chunk_2': 'third sentence',
            'chunks': 3,
            'chunk_prefix': 'chunk_',
            'analysis_label': 'Explanation',
            'analysis_type': 'explain',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'summarize', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")
