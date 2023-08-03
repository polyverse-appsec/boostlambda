from chalice.test import Client
from app import app
import json
import random

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
                            'package.json']
        realProjectFiles = random.sample(realProjectFiles, len(realProjectFiles))

        prioritizedListOfSourceFilesToAnalyze = ['package.json',
                                                 'src/extension.ts',
                                                 'src/test/suite/index.ts',
                                                 'src/test/suite/extension.test.ts',
                                                 ]

        projectFileList = realProjectFiles.copy()
        likelyExclusionList = ['src/info.txt',
                               'src/changelog.md',
                               'src/sample.html',
                               'src/branding.jpg']
        likelyExclusionList = random.sample(likelyExclusionList, len(likelyExclusionList))

        projectFileList.extend(likelyExclusionList)
        projectFileList = random.sample(projectFileList, len(projectFileList))

        request_body = {
            'filelist': projectFileList,
            'projectName': 'typescript-sample-extension',
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        draft_request_body = request_body.copy()
        response = client.lambda_.invoke(
            'draft-blueprint', draft_request_body)

        assert response.payload['statusCode'] == 200

        assert json.loads(response.payload['body'])['status'] == 1

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'draftBlueprint' in details
        assert 'recommendedSampleSourceFile' in details
        assert 'recommendedProjectDeploymentFile' in details
        assert 'recommendedListOfFilesToExcludeFromAnalysis' in details
        assert 'prioritizedListOfSourceFilesToAnalyze' in details

        # we want high confidence exclusions only
        excludedAtLeastOne = False
        for file in likelyExclusionList:
            if file in details['recommendedListOfFilesToExcludeFromAnalysis']:
                excludedAtLeastOne = True
                break
        assert excludedAtLeastOne

        def prioritize_files(projectFileList, prioritizedListOfSourceFiles):
            # Create a set for faster lookup of files in the prioritized list
            prioritized_set = set(prioritizedListOfSourceFiles)

            # Sort the files based on their priority and keep the default sort order for others
            sorted_files = sorted(projectFileList, key=lambda file: (file not in prioritized_set, prioritizedListOfSourceFiles.index(file)))

            return sorted_files

        for file in realProjectFiles:
            assert file in details['prioritizedListOfSourceFilesToAnalyze']

        for file in details['prioritizedListOfSourceFilesToAnalyze']:
            if file not in realProjectFiles:
                print(f"Prioritized analysis {file} is not in the real project files; expanded analysis may occur")

        proposedPriorityList = prioritize_files(realProjectFiles, details['prioritizedListOfSourceFilesToAnalyze'])
        if (proposedPriorityList != prioritizedListOfSourceFilesToAnalyze):
            print("Prioritized analysis list is not in the expected order; alterned analysis may occur")

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
