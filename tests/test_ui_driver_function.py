from chalice.test import Client
from app import app
import json

from .test_version import client_version


base_request_body = {
    'session': 'testemail: unittest@polytest.ai',
    'organization': 'polytest.ai',
    'version': client_version,
}


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
    ui_driver_helper('How do I use the prodoct to scan my code?', 'askForProductHelp')


def test_ui_driver_run_analysis():
    ui_driver_helper('Scan my project', 'startAnalysisOfProject')


def test_ui_driver_security_summary():
    ui_driver_helper('What is the security status of my project?', 'showSecuritySummaryOrStatus')


def test_ui_driver_compliance_summary():
    ui_driver_helper('What is the compliance status of my project?', 'showComplianceSummaryOrStatus')


def test_ui_driver_enable_security_analysis():
    ui_driver_helper('Turn on security analysis', 'enableSecurityAnalysis')


def test_ui_driver_unknown_operation():
    ui_driver_helper('Graph the source code changes over time on my project', 'unsupportedOperation')
