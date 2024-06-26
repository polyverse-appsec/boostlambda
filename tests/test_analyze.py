from chalice.test import Client
from app import app
import json

from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import

# load the data files into a string, relative to the root directory
with open('./tests/data/simple-buf.c', 'r') as file:
    simple_buf_c = file.read()


def test_analyze_function():
    with Client(app) as client:
        request_body = {
            'code': simple_buf_c,
            'inputMetadata': json.dumps({'lineNumberBase': 0}),
            'session': 'testemail: unittest@polytest.ai',
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

        assert len(analysis['details']) >= 3

        assert analysis['details'][0]['bugType'] == 'Buffer Overflow'
        assert analysis['details'][0]['lineNumber'] >= 13
        assert analysis['details'][0]['severity'] >= 7
        assert analysis['details'][1]['bugType'] != ''
        assert analysis['details'][1]['lineNumber'] >= 11
        assert analysis['details'][1]['severity'] >= 7
        # for this test, any string is fine
        assert analysis['details'][2]['bugType'] != ''
        assert analysis['details'][2]['lineNumber'] >= 14
        assert analysis['details'][2]['severity'] >= 6
