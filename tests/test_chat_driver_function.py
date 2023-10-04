from chalice.test import Client
from app import app
import json

from .test_version import client_version


base_request_body = {
    'session': 'testemail: unittest@polytest.ai',
    'organization': 'polytest.ai',
    'version': client_version,
}


class ChatActions:
    searchProjectWideAnalysis = 'searchProjectWideAnalysis'
    searchAnalysisOfASoureFile = 'searchAnalysisOfASoureFile'
    getHelpWithProductUsageOrDocumentation = 'getHelpWithProductUsageOrDocumentation'
    performUIOperation = 'performUIOperation'
    unsupportedOperation = 'unsupportedOperation'


def chat_driver_helper(
        userRequest,
        expected_action,
        filelist=None,
        includeSecurityAnalysisInfoForSearchContext=None,
        includeComplianceAnalysisInfoForSearchContext=None,
        targetSourceFiles=None):
    with Client(app) as client:
        request_body = base_request_body.copy()
        request_body['userRequest'] = userRequest
        request_body['filelist'] = filelist
        response = client.lambda_.invoke(
            'chat_driver', request_body)

        assert response.payload['statusCode'] == 200

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'chatAction' in details
        assert expected_action == details['chatAction']

        # if we are looking for a target file, make sure its in the AI response list
        if targetSourceFiles:
            assert 'targetSourceFiles' in details
            for targetSourceFile in targetSourceFiles:
                foundFile = False
                for searchFile in details['targetSourceFiles']:
                    if targetSourceFile in searchFile:
                        foundFile = True

                assert foundFile and targetSourceFile is not None

        if includeSecurityAnalysisInfoForSearchContext:
            assert 'includeSecurityAnalysisInfoForSearchContext' in details
            assert includeSecurityAnalysisInfoForSearchContext == details['includeSecurityAnalysisInfoForSearchContext']

        if includeComplianceAnalysisInfoForSearchContext:
            assert 'includeComplianceAnalysisInfoForSearchContext' in details
            assert includeComplianceAnalysisInfoForSearchContext == details['includeComplianceAnalysisInfoForSearchContext']


def test_chat_driver_help():
    chat_driver_helper('How do I use the product to find security issues?', ChatActions.getHelpWithProductUsageOrDocumentation)


def test_chat_driver_run_analysis():
    chat_driver_helper('Refresh analysis of my project', ChatActions.performUIOperation)


def test_chat_driver_security_summary():
    chat_driver_helper('What is the security status of my project?', ChatActions.searchProjectWideAnalysis,
                       None, includeSecurityAnalysisInfoForSearchContext=True)


def test_chat_driver_compliance_summary():
    chat_driver_helper('What is the compliance status of my project?', ChatActions.searchProjectWideAnalysis,
                       None, includeComplianceAnalysisInfoForSearchContext=True)


def test_chat_driver_enable_security_analysis():
    chat_driver_helper('Turn on security analysis', ChatActions.performUIOperation)


def test_chat_driver_nonexisting_ui_operation():
    chat_driver_helper('Create a new graph of the source code changes', ChatActions.unsupportedOperation)


def test_chat_driver_search_file():
    chat_driver_helper('What security issues are in socket file?', ChatActions.searchAnalysisOfASoureFile,
                       ['socket.py'],
                       includeSecurityAnalysisInfoForSearchContext=True)


def test_chat_driver_unknown_operation():
    chat_driver_helper('Can a giraffe grill a rocketship?', ChatActions.unsupportedOperation)
