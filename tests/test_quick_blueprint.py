from chalice.test import Client
from app import app
import json

# load the file data/simple-buf.c into a string, relative to the root directory
with open('./tests/data/quick-blueprint/package.json', 'r') as file:
    package_json = file.read()

with open('./tests/data/quick-blueprint/sample.ts', 'r') as file:
    sample_code_ts = file.read()

client_version = '0.9.5'


def test_quick_blueprint():
    with Client(app) as client:

        request_body = {
            'filelist': ['src/extension.ts',
                         'src/test/runTest.ts',
                         'src/test/suite/index.ts',
                         'src/test/suite/extension.test.ts',
                         'package.json'],
            'projectName': 'typescript-sample-extension',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'draft_blueprint', request_body)

        assert response.payload['statusCode'] == 200

        assert json.loads(response.payload['body'])['status'] == 1

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'draftBlueprint' in details
        assert 'recommendedSampleSourceFile' in details
        assert 'recommendedProjectDeploymentFile' in details

        request_body['projectFile'] = package_json
        request_body['draftBlueprint'] = details['draftBlueprint']
        request_body['code'] = sample_code_ts

        response = client.lambda_.invoke(
            'quick_blueprint', request_body)

        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        blueprint = json.loads(response.payload['body'])['blueprint']

        assert len(blueprint) > 0
        print(blueprint)

        assert request_body['projectName'] in blueprint

        # check for all sections in blueprint
        for header in ['Project Type', 'Principles', 'High-Level Summary',
                       'Data', 'Licensing', 'Security', 'Performance', 'resiliency', 'soundness', 'Problems Identified']:
            assert header in blueprint
