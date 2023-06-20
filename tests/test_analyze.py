from chalice.test import Client
from app import app
import json

client_version = '0.9.5'

def test_analyze_function():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'analyze_function', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200
