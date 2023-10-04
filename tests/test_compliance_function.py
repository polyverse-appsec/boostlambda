from chalice.test import Client
from app import app
import json

# load the file data into a string, relative to the root directory
with open('./tests/data/compliance/simple-compliance.js', 'r') as file:
    simple_buf_c = file.read()

from .test_version import client_version


def test_compliance_function():
    with Client(app) as client:
        request_body = {
            'code': simple_buf_c,
            'inputMetadata': json.dumps({'lineNumberBase': 0}),
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'compliance_function', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])
        assert analysis['status'] == 'bugsfound'

        assert len(analysis['details']) >= 2

        for issue in analysis['details']:
            assert ("PCI DSS" in issue['bugType'] or "GDPR" in issue['bugType'] or 'HIPAA' in issue['bugType'])
            assert issue['lineNumber'] >= 5
            assert issue['severity'] >= 2


def test_compliance():
    with Client(app) as client:
        request_body = {
            'code': simple_buf_c,
            'inputMetadata': json.dumps({'lineNumberBase': 0}),
            'outputFormat': 'rankedList',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'compliance', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])['analysis']

        assert len(analysis) > 0

        # check for at least 3 ranked issues
        assert 'Severity' in analysis
        assert '1. ' in analysis
        assert '2. ' in analysis
        assert '3. ' in analysis

        print(analysis)
