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

        # canned request_body to check the quick blueprint (without calling draft-blueprint)
        # request_body = {'filelist': ['src/test/suite/index.ts', 'src/extension.ts', 'src/test/suite/extension.test.ts', 'package.json', 'src/branding.jpg', 'src/info.txt', 'src/test/runTest.ts', 'src/changelog.md', 'src/sample.html'], 'projectName': 'typescript-sample-extension', 'session': 'testemail: unittest@polytest.ai', 'organization': 'polytest.ai', 'version': '0.9.5', 'projectFileList': ['src/test/runTest.ts', 'src/sample.html', 'package.json', 'src/extension.ts', 'src/test/suite/index.ts', 'src/test/suite/extension.test.ts'], 'projectFile': '{\n    "name": "typescript-sample-extension",\n    "displayName": "typescript-sample-extension",\n    "description": "sample extension for testing",\n    "version": "0.0.1",\n    "engines": {\n      "vscode": "^1.77.0"\n    },\n    "categories": [\n      "Other"\n    ],\n    "activationEvents": [],\n    "main": "./out/extension.js",\n    "contributes": {\n      "commands": [\n        {\n          "command": "typescript-sample-extension.helloWorld",\n          "title": "Run Sample TypeScript Extension"\n        },\n        {\n          "command": "typescript-sample-extension.showTimeInfo",\n          "title": "Show Current Time"\n        }\n      ]\n    },\n    "scripts": {\n      "vscode:prepublish": "npm run compile",\n      "compile": "tsc -p ./",\n      "watch": "tsc -watch -p ./",\n      "pretest": "npm run compile --verbose && npm run lint",\n      "lint": "eslint src --ext ts",\n      "test": "node ./out/test/runTest.js"\n    },\n    "devDependencies": {\n      "@types/glob": "^8.1.0",\n      "@types/mocha": "^10.0.1",\n      "@types/node": "16.x",\n      "@types/vscode": "^1.77.0",\n      "@typescript-eslint/eslint-plugin": "^5.56.0",\n      "@typescript-eslint/parser": "^5.56.0",\n      "@vscode/test-electron": "^2.3.0",\n      "eslint": "^8.36.0",\n      "glob": "^8.1.0",\n      "mocha": "^10.2.0",\n      "typescript": "^4.9.5",\n      "vscode-extension-tester": "^5.5.1"\n    }\n  }\n  ', 'draftBlueprint': 'Architectural Blueprint Summary for: typescript-sample-extension\n* Software Project Type: web app, server code, cloud web service, mobile app, shared library, etc.\n* High-Level Summary: Short summary of software project in a 2-3 sentences\n* Software Principles: multi-threaded, event-driven, data transformation, server processing, client app code, etc\n* Data Storage: shared memory, disk, database, SQL vs NoSQL, non-persisted, data separated from code\n* Software Licensing: Commercial & Non-Commercial licenses, Open Source licenses (BSD, MIT, GPL, LGPL, Apache, etc.). Identify conflicting licenses.\n* Security Handling: encrypted vs non-encrypted data, memory buffer management, shared memory protections, all input is untrusted or trusted\n* Performance characteristics: multi-threaded, non-blocking code, extra optimized, background tasks, CPU bound processing, etc.\n* Software resiliency patterns: fail fast, parameter validation, defensive code, error logging, etc.\n* Analysis of the architectural soundness and best practices: code is consistent with its programming language style, structure is consistent with its application or server framework\n* Architectural Problems Identified: coarse locks in multi-threaded, global and shared memory in library, UI in a non-interactive server, versioning fragility, etc.', 'code': '// The module \'vscode\' contains the VS Code extensibility API\n// Import the module and reference it with the alias vscode in your code below\nimport * as vscode from \'vscode\';\n\n// This method is called when your extension is activated\n// Your extension is activated the very first time the command is executed\nexport function activate(context: vscode.ExtensionContext) {\n\n\t// Use the console to output diagnostic information (console.log) and errors (console.error)\n\t// This line of code will only be executed once when your extension is activated\n\tconsole.log(\'Congratulations, your extension "typescript-sample-extension" is now active!\');\n\n\t// The command has been defined in the package.json file\n\t// Now provide the implementation of the command with registerCommand\n\t// The commandId parameter must match the command field in package.json\n\tlet disposable = vscode.commands.registerCommand(\'typescript-sample-extension.helloWorld\', () => {\n\t\t// The code you place here will be executed every time your command is executed\n\t\t// Display a message box to the user\n\t\tvscode.window.showInformationMessage(\'information about typescript-sample-extension!\');\n\t\tvscode.window.showWarningMessage(\'warning about typescript-sample-extension!\');\n\t\t\n\t});\n\n\tcontext.subscriptions.push(disposable);\n\n\tdisposable = vscode.commands.registerCommand(\'typescript-sample-extension.showTimeInfo\', () => {\n\t\tvscode.window.showInformationMessage(\'current time is \' + new Date().toLocaleTimeString());\n\t\t\n\t});\n\n\tcontext.subscriptions.push(disposable);\n}\n\n// This method is called when your extension is deactivated\nexport function deactivate() {}\n'}
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
