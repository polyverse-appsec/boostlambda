import json
import time

from chalicelib.auth import extract_client_version, fetch_orgs, fetch_email_and_username, userorganizations_api_version
from chalicelib.log import mins_and_secs
from chalicelib.telemetry import cloudwatch, xray_recorder
from chalicelib.app_utils import common_lambda_logic
from chalicelib.auth import ExtendedUnauthorizedError


def user_organizations_handler(event, context):
    def handler(event, correlation_id):
        # Extract parameters from the event object
        json_data = json.loads(event['body']) if 'body' in event else event
        client_version = extract_client_version(event)
        json_data['version'] = json_data.get('version', client_version)

        # if session is missing, the client isn't authorized
        if 'session' not in json_data:
            raise ExtendedUnauthorizedError("Invalid authentication/authorization", reason="InvalidSession")

        # Specific logic for user_organizations
        if cloudwatch is not None:
            with xray_recorder.capture('get_user_organizations'):
                orgs = fetch_orgs(json_data["session"])
                organizations = "NONE FOUND" if orgs is None else f"({','.join(orgs)})"
                email, username = fetch_email_and_username(json_data["session"])
        else:
            start_time = time.monotonic()
            orgs = fetch_orgs(json_data["session"])
            organizations = "NONE FOUND" if orgs is None else f"({','.join(orgs)})"
            email, username = fetch_email_and_username(json_data["session"])
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {mins_and_secs(end_time - start_time)}')

        print(f'BOOST_USAGE: email:{email}, organization:{organizations}, function({context.function_name}:{correlation_id}:{client_version}) SUCCEEDED')

        json_obj = {"organizations": orgs, "email": email, "personal": username}
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'X-API-Version': userorganizations_api_version},
            'body': json.dumps(json_obj)
        }

    return common_lambda_logic(event, context.function_name, handler, userorganizations_api_version)
