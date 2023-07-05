from chalice.test import Client
from app import app
import json

# load the file data/simple-buf.c into a string, relative to the root directory
with open('./tests/data/compliance/simple-compliance.js', 'r') as file:
    simple_buf_c = file.read()

client_version = '0.9.5'


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

        assert len(analysis['details']) >= 3

        assert 'PCI DSS' in analysis['details'][0]['bugType'] or 'Data Exposure' in analysis['details'][0]['bugType']
        assert analysis['details'][0]['severity'] >= 8
        assert analysis['details'][0]['lineNumber'] >= 5

        assert ("PCI DSS" in analysis['details'][1]['bugType'] or "GDPR" in analysis['details'][1]['bugType'] or 'HIPAA' in analysis['details'][1]['bugType'])
        assert analysis['details'][1]['lineNumber'] >= 4
        assert analysis['details'][1]['severity'] >= 7

        # for this test, any string is fine
        assert "PCI DSS" in analysis['details'][2]['bugType'] or "GDPR" in analysis['details'][2]['bugType'] or 'HIPAA' in analysis['details'][2]['bugType']
        assert analysis['details'][2]['lineNumber'] >= 2
        assert analysis['details'][2]['severity'] >= 7


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
