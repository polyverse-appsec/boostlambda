from chalice.test import Client
from app import app
# import json


def test_explain():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@darklight.ai'
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
            'session': 'testemail: alex@darklight.ai',
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
            'code': 'print("Hello, World!")'
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 401

        # now test with an email of alexgo@gmail.com
        request_body = {
            'session': 'testemail: alexgo@gmail.com',
            'code': 'print("Hello, World!")'
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 401

        # now test with an email of jkthecjer@gmail.com
        request_body = {
            'session': 'testemail: jkthecjer@gmail.com',
            'code': 'print("Hello, World!")'
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 200

        # now test with an email of alex@darklight.ai
        request_body = {
            'session': 'testemail: alex@darklight.ai',
            'code': 'print("Hello, World!")'
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
            'session': 'testemail: alex@darklight.ai'
        }
        response = client.lambda_.invoke(
            'testgen', request_body)

        assert response.payload['statusCode'] == 200


def test_analyze():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@darklight.ai'
        }

        response = client.lambda_.invoke(
            'analyze', request_body)

        assert response.payload['statusCode'] == 200


def test_compliance():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@darklight.ai'
        }

        response = client.lambda_.invoke(
            'compliance', request_body)

        assert response.payload['statusCode'] == 200


def test_codeguidelines():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@darklight.ai'
        }

        response = client.lambda_.invoke(
            'codeguidelines', request_body)

        assert response.payload['statusCode'] == 200
