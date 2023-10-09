from chalice.test import Client
from app import app
import json
import random
import os

from .test_utils import warn

# load the data files into a string, relative to the root directory
with open('./tests/data/quick-blueprint/package.json', 'r') as file:
    package_json = file.read()

with open('./tests/data/quick-blueprint/sample.ts', 'r') as file:
    sample_code_ts = file.read()

with open('./tests/data/quick-blueprint/package.json', 'r') as file:
    package_json = file.read()

with open('./tests/data/quick-blueprint/sample.ts', 'r') as file:
    sample_code_ts = file.read()

from .test_version import client_version

use_simulated_service_responses = False

os.environ["useNewThrottler"] = "True"


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
        if use_simulated_service_responses:
            request_body = {'filelist': ['src/test/suite/index.ts', 'src/extension.ts', 'src/test/suite/extension.test.ts', 'package.json', 'src/branding.jpg', 'src/info.txt', 'src/test/runTest.ts', 'src/changelog.md', 'src/sample.html'], 'projectName': 'typescript-sample-extension', 'session': 'testemail: unittest@polytest.ai', 'organization': 'polytest.ai', 'version': '0.9.5', 'projectFileList': ['src/test/runTest.ts', 'src/sample.html', 'package.json', 'src/extension.ts', 'src/test/suite/index.ts', 'src/test/suite/extension.test.ts'], 'projectFile': '{\n    "name": "typescript-sample-extension",\n    "displayName": "typescript-sample-extension",\n    "description": "sample extension for testing",\n    "version": "0.0.1",\n    "engines": {\n      "vscode": "^1.77.0"\n    },\n    "categories": [\n      "Other"\n    ],\n    "activationEvents": [],\n    "main": "./out/extension.js",\n    "contributes": {\n      "commands": [\n        {\n          "command": "typescript-sample-extension.helloWorld",\n          "title": "Run Sample TypeScript Extension"\n        },\n        {\n          "command": "typescript-sample-extension.showTimeInfo",\n          "title": "Show Current Time"\n        }\n      ]\n    },\n    "scripts": {\n      "vscode:prepublish": "npm run compile",\n      "compile": "tsc -p ./",\n      "watch": "tsc -watch -p ./",\n      "pretest": "npm run compile --verbose && npm run lint",\n      "lint": "eslint src --ext ts",\n      "test": "node ./out/test/runTest.js"\n    },\n    "devDependencies": {\n      "@types/glob": "^8.1.0",\n      "@types/mocha": "^10.0.1",\n      "@types/node": "16.x",\n      "@types/vscode": "^1.77.0",\n      "@typescript-eslint/eslint-plugin": "^5.56.0",\n      "@typescript-eslint/parser": "^5.56.0",\n      "@vscode/test-electron": "^2.3.0",\n      "eslint": "^8.36.0",\n      "glob": "^8.1.0",\n      "mocha": "^10.2.0",\n      "typescript": "^4.9.5",\n      "vscode-extension-tester": "^5.5.1"\n    }\n  }\n  ', 'draftBlueprint': 'Architectural Blueprint Summary for: typescript-sample-extension\n* Software Project Type: web app, server code, cloud web service, mobile app, shared library, etc.\n* High-Level Summary: Short summary of software project in a 2-3 sentences\n* Software Principles: multi-threaded, event-driven, data transformation, server processing, client app code, etc\n* Data Storage: shared memory, disk, database, SQL vs NoSQL, non-persisted, data separated from code\n* Software Licensing: Commercial & Non-Commercial licenses, Open Source licenses (BSD, MIT, GPL, LGPL, Apache, etc.). Identify conflicting licenses.\n* Security Handling: encrypted vs non-encrypted data, memory buffer management, shared memory protections, all input is untrusted or trusted\n* Performance characteristics: multi-threaded, non-blocking code, extra optimized, background tasks, CPU bound processing, etc.\n* Software resiliency patterns: fail fast, parameter validation, defensive code, error logging, etc.\n* Analysis of the architectural soundness and best practices: code is consistent with its programming language style, structure is consistent with its application or server framework\n* Architectural Problems Identified: coarse locks in multi-threaded, global and shared memory in library, UI in a non-interactive server, versioning fragility, etc.', 'code': '// The module \'vscode\' contains the VS Code extensibility API\n// Import the module and reference it with the alias vscode in your code below\nimport * as vscode from \'vscode\';\n\n// This method is called when your extension is activated\n// Your extension is activated the very first time the command is executed\nexport function activate(context: vscode.ExtensionContext) {\n\n\t// Use the console to output diagnostic information (console.log) and errors (console.error)\n\t// This line of code will only be executed once when your extension is activated\n\tconsole.log(\'Congratulations, your extension "typescript-sample-extension" is now active!\');\n\n\t// The command has been defined in the package.json file\n\t// Now provide the implementation of the command with registerCommand\n\t// The commandId parameter must match the command field in package.json\n\tlet disposable = vscode.commands.registerCommand(\'typescript-sample-extension.helloWorld\', () => {\n\t\t// The code you place here will be executed every time your command is executed\n\t\t// Display a message box to the user\n\t\tvscode.window.showInformationMessage(\'information about typescript-sample-extension!\');\n\t\tvscode.window.showWarningMessage(\'warning about typescript-sample-extension!\');\n\t\t\n\t});\n\n\tcontext.subscriptions.push(disposable);\n\n\tdisposable = vscode.commands.registerCommand(\'typescript-sample-extension.showTimeInfo\', () => {\n\t\tvscode.window.showInformationMessage(\'current time is \' + new Date().toLocaleTimeString());\n\t\t\n\t});\n\n\tcontext.subscriptions.push(disposable);\n}\n\n// This method is called when your extension is deactivated\nexport function deactivate() {}\n'}
        else:
            response = client.lambda_.invoke(
                'quick-blueprint', request_body)

        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        blueprint = json.loads(response.payload['body'])['blueprint']

        assert len(blueprint) > 0
        print(blueprint)

        assert request_body['projectName'] in blueprint

        # check for all sections in blueprint
        for header in ['Project Type', 'Principles', 'High-Level Summary', 'Test / Quality Strategy',
                       'Data', 'Licensing', 'Security', 'Performance', 'resiliency', 'soundness', 'Problems Identified']:
            assert header in blueprint


COMMON_FILENAMES = [
    'app', 'index', 'main', 'controller', 'model', 'service', 'utils', 'config', 'routes',
    'test', 'data', 'view', 'component', 'template', 'settings', 'helpers', 'manager', 'handler',
    'provider', 'factory', 'repository', 'middleware', 'auth', 'authenticator', 'logger', 'formatter',
    'validator', 'serializer', 'reader', 'writer', 'initializer', 'loader', 'generator', 'parser',
    'encoder', 'decoder', 'transformer', 'resolver', 'connector', 'mapper', 'scheduler', 'listener',
    'subscriber', 'publisher', 'worker', 'worker', 'executor', 'monitor', 'observer', 'notifier'
]


def generate_random_file_paths(num_folders, num_files_per_folder):
    extensions = ['cs', 'py', 'c', 'rb', 'html', 'css', 'cpp', 'java', 'pl']
    folder_names = generate_realistic_folder_names()
    file_bases = generate_realistic_file_bases()
    file_paths = set()

    for folder_idx in range(num_folders):
        folder_name = random.choice(folder_names)
        num_subfolders = random.randint(0, 5)
        subfolder_path = '/'.join(random.choice(folder_names) for _ in range(num_subfolders)) + '/' if num_subfolders != 0 else ''
        for file_idx in range(num_files_per_folder):
            unique_path_found = False
            while not unique_path_found:
                extension = random.choice(extensions)
                file_base = random.choice(file_bases)
                file_name = f'{file_base}.{extension}'
                random_file_path = f'{subfolder_path}{folder_name}/{file_name}'
                if random_file_path not in file_paths:
                    unique_path_found = True
                    file_paths.add(random_file_path)
                    if random_file_path.startswith('/'):
                        print("random_file_path starts with /")

    return list(file_paths)


def generate_realistic_file_bases():
    return COMMON_FILENAMES


def generate_realistic_project_name():
    project_prefixes = ['awesome', 'modern', 'smart', 'fast', 'efficient', 'ultimate', 'innovative', 'powerful', 'nextgen', 'pro', 'enterprise']
    project_keywords = ['web', 'app', 'platform', 'solution', 'system', 'tool', 'service', 'framework', 'engine', 'library', 'application']

    return f'{random.choice(project_prefixes)}-{random.choice(project_keywords)}'


# https://en.wikipedia.org/wiki/Kendall_rank_correlation_coefficient
def kendalls_tau(list1, list2):
    all_items = set(list1) | set(list2)

    rank1 = {item: (list1.index(item) if item in list1 else len(list1) + len(list2)) for item in all_items}
    rank2 = {item: (list2.index(item) if item in list2 else len(list1) + len(list2)) for item in all_items}

    n = len(all_items)

    pairs = [(rank1[item], rank2[item]) for item in all_items]

    # Count concordant and discordant pairs
    C, D = 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            if (pairs[i][0] < pairs[j][0] and pairs[i][1] < pairs[j][1]) or (pairs[i][0] > pairs[j][0] and pairs[i][1] > pairs[j][1]):
                C += 1
            elif (pairs[i][0] < pairs[j][0] and pairs[i][1] > pairs[j][1]) or (pairs[i][0] > pairs[j][0] and pairs[i][1] < pairs[j][1]):
                D += 1

    return (C - D) / (C + D) if (C + D) != 0 else 0


def test_quick_blueprint_fixed_tiny_project():
    helper_test_quick_blueprint_large_project(1, False)


def test_quick_blueprint_random_tiny_project():
    helper_test_quick_blueprint_large_project(1, True)


def test_quick_blueprint_fixed_small_project():
    helper_test_quick_blueprint_large_project(10, False)


def test_quick_blueprint_random_small_project():
    helper_test_quick_blueprint_large_project(10, True)


def test_quick_blueprint_fixed_medium_project():
    helper_test_quick_blueprint_large_project(20, False)


def test_quick_blueprint_random_medium_project():
    helper_test_quick_blueprint_large_project(20, True)


def test_quick_blueprint_fixed_large_project():
    helper_test_quick_blueprint_large_project(50, False)


def test_quick_blueprint_random_large_project():
    helper_test_quick_blueprint_large_project(50, True)


def helper_test_quick_blueprint_large_project(size, randomize):
    with Client(app) as client:
        if randomize:
            num_folders = random.randint(10, size)
            num_files_per_folder = random.randint(10, size * 2)
        else:
            num_folders = size
            num_files_per_folder = size * 2

        realProjectFiles = generate_random_file_paths(num_folders, num_files_per_folder)
        prioritizedListOfSourceFilesToAnalyze = generate_prioritized_file_list(realProjectFiles)
        likelyExclusionList = generate_likely_exclusion_list(realProjectFiles, generate_realistic_folder_names())

        projectFileList = realProjectFiles.copy()
        projectFileList.extend(likelyExclusionList)
        random.shuffle(projectFileList)

        project_name = generate_realistic_project_name()

        request_body = {
            'filelist': projectFileList,
            'projectName': project_name,
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        if use_simulated_service_responses:
            response = (lambda **kwargs: type("Response", (object,), kwargs))(payload={
                'statusCode': 200,
                'body': '{"status": 1, "details": {"draftBlueprint": "## Architectural Blueprint Summary for: ultimate-application\\n* Software Project Type: web app, server code, cloud web service, mobile app, shared library, etc.\\n* High-Level Summary: Short summary of software project in a 2-3 sentences\\n* Programming Languages: List of programming languages used in project\\n* Software Principles: multi-threaded, event-driven, data transformation, server processing, client app code, etc\\n* Test / Quality Strategy: Unit-tests, functional tests, test framework, and test language\\n* Data Storage: shared memory, disk, database, SQL vs NoSQL, non-persisted, data separated from code\\n* Software Licensing: Commercial & Non-Commercial licenses, Open Source licenses (BSD, MIT, GPL, LGPL, Apache, etc.). Identify conflicting licenses.\\n* Security Handling: encrypted vs non-encrypted data, memory buffer management, shared memory protections, all input is untrusted or trusted\\n* Performance characteristics: multi-threaded, non-blocking code, extra optimized, background tasks, CPU bound processing, etc.\\n* Software resiliency patterns: fail fast, parameter validation, defensive code, error logging, etc.\\n* Analysis of the architectural soundness and best practices: code is consistent with its programming language style, structure is consistent with its application or server framework\\n* Architectural Problems Identified: coarse locks in multi-threaded, global and shared memory in library, UI in a non-interactive server, versioning fragility, etc.", "recommendedSampleSourceFile": "routes/ui/connector.java", "recommendedProjectDeploymentFile": "public/middleware/client/assets/connector.rb", "recommendedListOfFilesToExcludeFromAnalysis": ["public/file_16.png", "private/controller.css", "views/resources/auth/tests/views/tests/worker.html", "tests/models/tests/auth/public/client/transformer.html", "views/resources/auth/tests/views/tests/config.html", "private/utils.html", "views/resources/auth/tests/views/tests/main.html", "tests/models/tests/auth/public/client/encoder.css", "routes/ui/formatter.css", "tests/models/tests/auth/public/client/parser.css", "routes/ui/template.html", "assets/ui/database/validator.html", "resources/utils/file_27.bin", "views/resources/auth/tests/views/tests/config.html", "utils/scheduler.html", "assets/ui/database/executor.html", "routes/ui/observer.html", "utils/publisher.css", "tests/models/tests/auth/public/client/authenticator.html", "public/middleware/client/assets/component.html"], "prioritizedListOfSourceFilesToAnalyze": ["routes/ui/connector.java", "private/connector.py", "ui/utils/client/routes/formatter.pl", "models/api/routes/views/private/component.c", "ui/utils/client/routes/helpers.java", "tests/models/tests/auth/public/client/notifier.cpp", "models/api/routes/views/private/scheduler.rb", "tests/routes/api/logger.py", "utils/writer.py", "routes/ui/authenticator.cpp", "public/middleware/client/assets/connector.rb", "views/resources/auth/tests/views/tests/handler.java", "tests/models/tests/auth/public/client/handler.cs", "tests/routes/api/index.pl", "models/api/routes/views/private/repository.cs", "ui/utils/client/routes/subscriber.py", "private/executor.java", "public/middleware/client/assets/main.cs", "private/executor.pl", "public/middleware/client/assets/notifier.py", "views/resources/auth/tests/views/tests/writer.pl", "assets/ui/database/mapper.cs", "models/api/routes/views/private/reader.rb", "assets/ui/database/index.cpp", "routes/ui/subscriber.pl", "public/middleware/client/assets/observer.c", "tests/routes/api/settings.cs", "public/middleware/client/assets/parser.pl", "views/resources/auth/tests/views/tests/parser.java", "private/subscriber.c", "ui/utils/client/routes/parser.pl", "assets/ui/database/authenticator.pl", "models/api/routes/views/private/template.cpp", "models/api/routes/views/private/worker.java", "ui/utils/client/routes/connector.java", "ui/utils/client/routes/logger.java", "routes/ui/worker.java", "private/config.cs", "views/resources/auth/tests/views/tests/routes.py", "assets/ui/database/test.cpp", "tests/routes/api/repository.java", "tests/routes/api/generator.py", "models/api/routes/views/private/model.py", "views/resources/auth/tests/views/tests/writer.pl", "assets/ui/database/resolver.pl", "utils/handler.pl", "assets/ui/database/utils.java", "routes/ui/reader.pl", "utils/worker.java", "ui/utils/client/routes/initializer.rb", "utils/writer.cpp", "routes/ui/manager.pl", "ui/utils/client/routes/handler.pl", "models/api/routes/views/private/mapper.py", "tests/models/tests/auth/public/client/worker.cpp", "tests/routes/api/reader.css", "tests/models/tests/auth/public/client/handler.cs", "tests/models/tests/auth/public/client/decoder.css", "models/api/routes/views/private/worker.cs", "public/middleware/client/assets/worker.java", "utils/helpers.pl", "tests/routes/api/view.py", "assets/ui/database/main.java", "tests/routes/api/executor.cs", "public/middleware/client/assets/scheduler.py", "ui/utils/client/routes/mapper.cs", "ui/utils/client/routes/service.rb", "public/middleware/client/assets/reader.c", "assets/ui/database/utils.cs", "utils/middleware.cpp", "private/test.cs", "utils/parser.cpp", "models/api/routes/views/private/validator.cs", "tests/models/tests/auth/public/client/view.pl", "utils/test.java", "routes/ui/authenticator.rb", "private/controller.pl", "tests/routes/api/service.c", "public/middleware/client/assets/authenticator.java"]}, "account": {"enabled": true, "status": "paid", "org": "polytest.ai", "email": "unittest@polytest.ai"}}'
            })
        else:
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
        excludedAtLeastOne = 0
        for file in likelyExclusionList:
            if file in details['recommendedListOfFilesToExcludeFromAnalysis']:
                excludedAtLeastOne += 1
                break
        highConfidenceExclusion = excludedAtLeastOne / len(likelyExclusionList)
        print(f"High Confidence Exclusions: {highConfidenceExclusion * 100:.2f}%")
        warn(lambda: highConfidenceExclusion > 0.8)

        def prioritize_files(projectFileList, prioritizedListOfSourceFiles):
            # Create a set for faster lookup of files in the prioritized list
            prioritized_set = set(prioritizedListOfSourceFiles)

            # Sort the files based on their priority and keep the default sort order for others
            #   ignore files not found in the 2nd prioritized list
            sorted_files = sorted(projectFileList, key=lambda file: (file not in prioritized_set, prioritizedListOfSourceFiles.index(file) if file in prioritizedListOfSourceFiles else float('inf')))

            return sorted_files

        # we're looking for most files to be included... since some variance
        matchedPrioritizedFiles = 0
        for file in realProjectFiles:
            if file in details['prioritizedListOfSourceFilesToAnalyze']:
                matchedPrioritizedFiles += 1

        # we want at least 80% of the files to be included
        highConfidencePrioritized = matchedPrioritizedFiles > len(realProjectFiles)
        print(f"High Confidence Prioritized: {highConfidencePrioritized * 100:.2f}%")
        warn(lambda: highConfidencePrioritized > 0.8)

        falseInclusions = 0
        for file in details['prioritizedListOfSourceFilesToAnalyze']:
            if file not in realProjectFiles:
                falseInclusions += 1
                print(f"Prioritized analysis {file} is not in the real project files; expanded analysis may occur")

        # we want no more than 20% false inclusions
        avoidFalseInclusions = falseInclusions < len(realProjectFiles)
        print(f"Avoid False Inclusions: {avoidFalseInclusions * 100:.2f}%")
        warn(lambda: avoidFalseInclusions < 0.2)

        proposedPriorityList = prioritize_files(realProjectFiles, details['prioritizedListOfSourceFilesToAnalyze'])
        # confirm the lists are mostly highly correlated
        correlation = kendalls_tau(proposedPriorityList, prioritizedListOfSourceFilesToAnalyze)
        if correlation < 0.7:
            print(f"Prioritized analysis lists are not in the similar order ({correlation} correlation); altered analysis may occur")

        # but we don't want to exclude real source ever
        realSourceExcluded = 0
        for file in realProjectFiles:
            if file not in details['recommendedListOfFilesToExcludeFromAnalysis']:
                realSourceExcluded += 1

        # we want no more than 10% real source excluded
        avoidRealSourceExclusion = realSourceExcluded < len(realProjectFiles)
        print(f"Avoid Real Source Exclusion: {avoidRealSourceExclusion * 100:.2f}%")
        warn(lambda: avoidRealSourceExclusion < 0.1)

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

        # We can't check the project name or source since its completely mismatched to the random files
        #    This functional test is for large filelists, not the details of the blueprint
        # assert request_body['projectName'] in blueprint

        # check for all sections in blueprint
        for header in ['Project Type', 'Principles', 'High-Level Summary', 'Test / Quality Strategy',
                       'Data', 'Licensing', 'Security', 'Performance', 'resiliency', 'soundness', 'Problems Identified']:
            assert header in blueprint


def generate_likely_exclusion_list(file_paths, folder_names):
    extensions = ['txt', 'bin', 'jpg', 'png']

    # generate 20% extra files for exclusion
    num_files_to_exclude = random.randint(1, max(1, len(file_paths) // 5))

    exclusion_file_paths = []
    for _ in range(num_files_to_exclude):
        num_folders = random.randint(0, 5)
        folder_path = '/'.join([random.choice(folder_names) for _ in range(num_folders)]) + '/' if num_folders != 0 else ''
        extension = random.choice(extensions)
        file_name = f'file_{random.randint(1, 100)}.{extension}'
        if folder_path == '/':
            print("folder_path is /")
        exclusion_file_paths.append(f'{folder_path}{file_name}')

    return exclusion_file_paths


def generate_realistic_folder_names():
    return [
        'ui', 'base', 'core', 'api', 'client', 'server', 'database',
        'views', 'controllers', 'models', 'utils', 'tests', 'config',
        'public', 'private', 'auth', 'resources', 'assets', 'middleware',
        'routes'
    ]


def generate_prioritized_file_list(file_paths):
    num_files_to_prioritize = random.randint(1, len(file_paths) // 2)
    return random.sample(file_paths, num_files_to_prioritize)
