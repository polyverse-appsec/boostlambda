from chalice.test import Client
from app import app
import json

# load the file data/simple-buf.c into a string, relative to the root directory
with open('./tests/data/simple-compliance.js', 'r') as file:
    simple_buf_c = file.read()

client_version = '0.9.5'


def test_compliance_function():
    with Client(app) as client:
        request_body = {
            'code': simple_buf_c,
            'inputMetadata': json.dumps({'lineNumberBase': 0}),
            'session': 'testemail: alex@polytest.ai',
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
        assert 'PCI DSS' in analysis['details'][0]['bugType']
        assert analysis['details'][0]['severity'] >= 10
        assert analysis['details'][0]['lineNumber'] >= 5

        assert ("PCI DSS" in analysis['details'][1]['bugType'] or "GDPR" in analysis['details'][1]['bugType'] or 'HIPAA' in analysis['details'][1]['bugType'])
        assert analysis['details'][1]['lineNumber'] >= 4
        assert analysis['details'][1]['severity'] >= 7

        # for this test, any string is fine
        assert "PCI DSS" in analysis['details'][2]['bugType']
        assert analysis['details'][2]['lineNumber'] >= 4
        assert analysis['details'][2]['severity'] >= 7
