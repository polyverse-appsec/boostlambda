from chalice.test import Client
from app import app
import json

# load the file data/simple-buf.c into a string, relative to the root directory
with open('./tests/data/simple-buf.c', 'r') as file:
    simple_buf_c = file.read()

client_version = '0.9.5'


def test_analyze_function():
    with Client(app) as client:
        request_body = {
            'code': simple_buf_c,
            'inputMetadata': json.dumps({'lineNumberBase': 0}),
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'analyze_function', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200
        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])
        assert analysis['status'] == 'bugsfound'
        assert analysis['details'][0]['bugType'] == 'Buffer Overflow'
        assert analysis['details'][0]['lineNumber'] >= 15
        assert analysis['details'][0]['severity'] >= 7
        assert analysis['details'][1]['bugType'] != ''
        assert analysis['details'][1]['lineNumber'] >= 15
        assert analysis['details'][1]['severity'] >= 7
        # for this test, any string is fine
        assert analysis['details'][2]['bugType'] != ''
        assert analysis['details'][2]['lineNumber'] >= 14
        assert analysis['details'][2]['severity'] >= 7
