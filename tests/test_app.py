from chalice.test import Client
from app import app
import json

client_version = '0.9.5'


def test_explain():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200


def test_explain_with_guideline():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'guidelines': ['system',
                           ['This application code should be able to print "Hello, Cruel World!" to the console.',
                            'This application code should be written in TypeScript or JavaScript.']],
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200


def test_generate_outputlanguage():
    with Client(app) as client:
        output_language = 'python'  # Replace this with the desired output language
        request_body = {
            'explanation': 'This is a simple program that prints "Hello, World!" to the console.',
            'originalCode': 'print("Hello, World!")',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version,
            'output_language': output_language
        }
        response = client.lambda_.invoke(
            'generate', request_body)

        assert response.payload['statusCode'] == 200


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

        # now test with an email of alex@polytest.ai
        request_body = {
            'session': 'testemail: alex@polytest.ai',
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
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }
        response = client.lambda_.invoke(
            'testgen', request_body)

        assert response.payload['statusCode'] == 200


def test_analyze():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'analyze', request_body)

        assert response.payload['statusCode'] == 200


def test_compliance():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'compliance', request_body)

        assert response.payload['statusCode'] == 200


def test_codeguidelines():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'codeguidelines', request_body)

        assert response.payload['statusCode'] == 200


def test_blueprint():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'guidelines': ['system',
                           ['This application code should be able to print "Hello, Cruel World!" to the console.',
                            'This application code should be written in TypeScript or JavaScript.']],
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'codeguidelines', request_body)

        assert response.payload['statusCode'] == 200


def test_customprocess():
    with Client(app) as client:
        code = 'print("Hello, World!")'
        prompt = "Analyze this code to identify use of code incompatible with a commercial license, such as any open source license.\n\nExamples of licenses include BSD, MIT, GPL, LGPL, Apache or other licenses that may conflict with commercial licenses.\n\nFor any identified licenses in the code, provide online web links to relevant license analysis.\n\n\n" + code
        this_role_system = "I am a sofware architect bot. I will analyze the code for architectural, algorithmic and design issues."
        request_body = {
            'code': code,
            'prompt': prompt,
            'messages': json.dumps([
                {
                    "role": "system",
                    "content": this_role_system
                },
                {
                    "role": "user",
                    "content": prompt
                }]),
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'customprocess', request_body)

        assert response.payload['statusCode'] == 200
