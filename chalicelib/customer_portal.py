import json
import time

from chalicelib.auth import extract_client_version
from chalicelib.log import mins_and_secs
from chalicelib.payments import customer_portal_url, customerportal_api_version
from chalicelib.app_utils import validate_request_lambda, common_lambda_logic


def customer_portal_handler(event, context):
    def handler(event, correlation_id):
        # Extract parameters from the event object
        json_data = json.loads(event['body']) if 'body' in event else event

        headers = event['headers'] if 'headers' in event else event

        client_version = extract_client_version(event)
        json_data['version'] = json_data.get('version', client_version)
        organization = json_data.get('organization')

        # Validate request lambda
        account = validate_request_lambda(json_data, headers, context.function_name, correlation_id, False)

        # Specific logic for customer_portal
        email = account['email'] if 'email' in account else None

        if not account['enabled'] and account['status'] not in ('suspended', 'expired'):
            status = account['status']
            session = None
            print(f'{status}: email:{email}, organization:{organization}, function({context.function_name}:{correlation_id}:{client_version}) No Customer Portal generated')
        else:
            # Now call the customer_portal_url function
            start_time = time.monotonic()
            session = customer_portal_url(account)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} portal: {mins_and_secs(end_time - start_time)}')

        # Prepare the account information
        if 'customer' in account:
            del account['customer']
        if 'subscription' in account:
            del account['subscription']
        if 'subscription_item' in account:
            del account['subscription_item']

        if session is None:
            account["portal_url"] = None
        elif account["email"] != account["owner"]:
            if account["email"].endswith(("@polyverse.io", "@polytest.ai", "@polyverse.com")):
                account["portal_url"] = session.url
            else:
                account["portal_url"] = None
        else:
            account["portal_url"] = session.url

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'X-API-Version': customerportal_api_version},
            'body': json.dumps(account)
        }

    return common_lambda_logic(event, context.function_name, handler, customerportal_api_version)
