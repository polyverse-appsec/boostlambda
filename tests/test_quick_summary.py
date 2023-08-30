from chalice.test import Client
from app import app
import json

try:
    # examples of high-severity analysis in json
    with open('./tests/data/quick-compliance/severity_analysis.json', 'r') as file:
        sample_analysis_json = file.read()

    # high-level categorization of severities and categories in json
    with open('./tests/data/quick-compliance/categorizations.json', 'r') as file:
        categorizations_json = file.read()

    with open('./tests/data/quick-compliance/files.json', 'r') as file:
        filelist_json = file.read()

except Exception as e:
    print(f"Error loading test data: {str(e)}")

from test_version import client_version


def test_quick_compliance():
    with Client(app) as client:

        projectFileList = json.loads(filelist_json)

        request_body = {
            'filelist': projectFileList,
            'examples': sample_analysis_json,
            'issue_categorization': categorizations_json,

            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'quick-summary', request_body)

        assert response.payload['statusCode'] == 200

        # function creates details from an embedded JSON string
        summary = json.loads(response.payload['body'])['summary']
        lower_summary = summary.lower()

        print("\n\n" + summary + "\n\n\n\n")

        assert '395' in lower_summary
        assert 'risk' in lower_summary
        assert 'impact' in lower_summary
        assert 'gdpr' in lower_summary
        assert 'hipaa' in lower_summary
        assert 'hardcoded' in lower_summary
