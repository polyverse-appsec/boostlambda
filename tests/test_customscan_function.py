from chalice.test import Client
from app import app
import json

# load the file data/simple-buf.c into a string, relative to the root directory
with open('./tests/data/customscan/missingawait.ts', 'r') as file:
    missingawait_ts = file.read()

from .test_version import client_version


def test_customscan_function():
    with Client(app) as client:
        request_body = {
            'code': missingawait_ts,
            'inputMetadata': json.dumps({'lineNumberBase': 2820}),
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        request_body['customScanGuidance'] = (
            'broken or incorrect handling of asynchronous code. \n'
            'Look for any of following issues:\n'
            '* code that leaks threads, wasting memory or thread pool resources\n'
            '* uses multiple threads to operate on unsafe or shared resources without locking\n'
            '* incorrect synchronization, including missing joins or waits\n'
            '* misuse of locks that can lead to livelocks and deadlocks '
            'including lock order inversions or race conditions.\n'
            '* code that might exit prematurely without resolving or '
            'rejecting a promise or its language-specific equivalent\n')

        request_body['customScanCategories'] = 'ResourceLeak, UnsafeResource, Deadlock, Livelock, MissingSync'
        # request_body['scanTypeDescription'] = 'The type of synchronization issue, e.g. "ResourceLeak", \
        # "UnsafeResource", using one of the following types: ResourceLeak, UnsafeResource, Deadlock, Livelock, \
        # MissingSync'

        response = client.lambda_.invoke('customscan_function', request_body)

        print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])
        assert analysis['status'] == 'bugsfound'

        assert len(analysis['details']) >= 1

        foundSyncIssue = False
        for issue in analysis['details']:
            if issue['bugType'] != 'MissingSync':
                continue
            if issue['severity'] < 4:
                continue
            if 'promise' not in issue['description'].lower() and 'await' not in issue['description'].lower():
                continue

            foundSyncIssue = True

        if not foundSyncIssue:
            print("No sync issue found in analysis")
            print(analysis['details'])

        assert foundSyncIssue
