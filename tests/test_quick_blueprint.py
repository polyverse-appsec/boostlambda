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

        realProjectFiles = ['src/extension.ts',
                            'src/test/runTest.ts',
                            'src/test/suite/index.ts',
                            'src/test/suite/extension.test.ts',
                            'src/test/suite/extension.test.ts',
                            'package.json']
        projectFileList = realProjectFiles.copy()
        likelyExclusionList = ['src/info.txt',
                               'src/changelog.md',
                               'src/sample.html',
                               'src/branding.jpg']
        projectFileList.extend(likelyExclusionList)
        request_body = {
            'filelist': projectFileList,
            'projectName': 'typescript-sample-extension',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'draft-blueprint', request_body)

        assert response.payload['statusCode'] == 200

        assert json.loads(response.payload['body'])['status'] == 1

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'draftBlueprint' in details
        assert 'recommendedSampleSourceFile' in details
        assert 'recommendedProjectDeploymentFile' in details
        assert 'recommendedListOfFilesToExcludeFromAnalysis' in details

        # we want high confidence exclusions only
        excludedAtLeastOne = False
        for file in likelyExclusionList:
            if file in details['recommendedListOfFilesToExcludeFromAnalysis']:
                excludedAtLeastOne = True
                break
        assert excludedAtLeastOne

        # but we don't want to exclude real source ever
        for file in realProjectFiles:
            assert file not in details['recommendedListOfFilesToExcludeFromAnalysis']

        request_body['projectFileList'] = list(set(projectFileList) - set(details['recommendedListOfFilesToExcludeFromAnalysis']))
        request_body['projectFile'] = package_json
        request_body['draftBlueprint'] = details['draftBlueprint']
        request_body['code'] = sample_code_ts

        response = client.lambda_.invoke(
            'quick-blueprint', request_body)

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
