from chalice.test import Client
from app import app
import json

from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


base_request_body = {
    'session': 'testemail: unittest@polytest.ai',
    'organization': 'polytest.ai',
    'version': client_version,
}


class UIActions:
    askForProductHelp = 'askForProductHelp'
    startAnalysisOfProject = 'startAnalysisOfProject'
    showProjectSummaryOrOverallStatus = 'showProjectSummaryOrOverallStatus'
    showSecuritySummaryOrStatus = 'showSecuritySummaryOrStatus'
    showComplianceSummaryOrStatus = 'showComplianceSummaryOrStatus'
    enableSecurityAnalysis = 'enableSecurityAnalysis'
    disableSecurityAnalysis = 'disableSecurityAnalysis'
    enableComplianceAnalysis = 'enableComplianceAnalysis'
    disableComplianceAnalysis = 'disableComplianceAnalysis'
    enableDocumentationGeneration = 'enableDocumentationGeneration'
    disableDocumentationGeneration = 'disableDocumentationGeneration'
    unsupportedOperation = 'unsupportedOperation'


def ui_driver_helper(userCommand, expected_uiAction):
    with Client(app) as client:
        request_body = base_request_body.copy()
        request_body['userCommand'] = userCommand
        response = client.lambda_.invoke(
            'ui_driver', request_body)

        assert response.payload['statusCode'] == 200

        # function creates details from an embedded JSON string
        details = json.loads(response.payload['body'])['details']

        print(details)

        assert 'uiAction' in details
        assert expected_uiAction == details['uiAction']


def test_ui_driver_help():
    ui_driver_helper('How do I use the prodoct to scan my code?', UIActions.askForProductHelp)


def test_ui_driver_run_analysis():
    ui_driver_helper('Scan my project', UIActions.startAnalysisOfProject)


def test_ui_driver_security_summary():
    ui_driver_helper('What is the security status of my project?', UIActions.showSecuritySummaryOrStatus)


def test_ui_driver_compliance_summary():
    ui_driver_helper('What is the compliance status of my project?', UIActions.showComplianceSummaryOrStatus)


def test_ui_driver_enable_security_analysis():
    ui_driver_helper('Turn on security analysis', UIActions.enableSecurityAnalysis)


def test_ui_driver_unknown_operation():
    ui_driver_helper('Graph the source code changes over time on my project', UIActions.unsupportedOperation)
