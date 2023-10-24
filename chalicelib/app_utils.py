
import traceback
import json
import uuid
import time
import os

from chalice import BadRequestError
from chalicelib.log import mins_and_secs

from chalicelib.telemetry import cloudwatch, xray_recorder
from chalicelib.auth import \
    validate_request_lambda, \
    clean_account, \
    extract_client_version

from chalicelib.aws import \
    init_current_lambda_cost


def process_request(event, function, api_version):
    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    init_current_lambda_cost(correlation_id)

    email = "unknown"  # in case we fail early and don't get the email address
    organization = "unknown"
    account = None

    print(f'Inbound request {correlation_id} {function.__name__}')

    try:
        # Extract parameters from the event object
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        client_version = extract_client_version(event)
        if ('version' not in json_data):
            json_data['version'] = client_version
        else:
            client_version = json_data['version']

        organization = json_data.get('organization')

        # Capture the duration of the validation step
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                # first we check if the account is enabled
                account = validate_request_lambda(json_data, function.__name__, correlation_id, False)

                email = account['email'] if 'email' in account else email

                # if not enabled, then we're going to raise an error
                # note: we could return the error in the account object and save
                # calling validate again, but for now, we're going to keep it simple
                if not (account['enabled'] if 'enabled' in account else False):
                    validate_request_lambda(json_data, function.__name__, correlation_id, True)
        else:
            start_time = time.monotonic()
            account = validate_request_lambda(json_data, function.__name__, correlation_id, False)

            email = account['email'] if 'email' in account else email

            # if not enabled, then we're going to raise an error
            # note: we could return the error in the account object and save
            # calling validate again, but for now, we're going to keep it simple
            if not (account['enabled'] if 'enabled' in account else False):
                try:
                    validate_request_lambda(json_data, function.__name__, correlation_id, True)
                finally:
                    end_time = time.monotonic()
                    print(f'Execution time {correlation_id} validate_request FAILED: {mins_and_secs(end_time - start_time)}')
            else:
                end_time = time.monotonic()
                print(f'Execution time {correlation_id} validate_request: {mins_and_secs(end_time - start_time)}')

        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the function
        if cloudwatch is not None:
            with xray_recorder.capture(function.__name__):
                result = function(json_data, account, function.__name__, correlation_id)
        else:
            start_time = time.monotonic()
            result = function(json_data, account, function.__name__, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} {function.__name__}: {mins_and_secs(end_time - start_time)}')

        print(f'BOOST_USAGE: email:{email}, organization:{organization}, function({function.__name__}:{correlation_id}:{client_version}) SUCCEEDED')

    except Exception as e:
        exception_info = traceback.format_exc().replace('\n', ' ')
        serviceFailureDetails = str(e)

        # Use the get() method to retrieve the value of CHALICE_STAGE, with a default value of 'local' - e.g. local debugging
        service_stage = os.environ.get('CHALICE_STAGE', 'local')

        serviceLogFailurePrefix = "BOOST_USAGE: "
        # we want to catch internal implementation errors and return a 500
        if isinstance(e, (UnboundLocalError, TypeError, ValueError, KeyError, IndexError, AttributeError, RuntimeError, NotImplementedError)):
            serviceLogFailurePrefix = "SERVICE_IMPL_FAILURE: " + serviceLogFailurePrefix

        elif isinstance(e, (BadRequestError)):
            serviceLogFailurePrefix = "CLIENT_IMPL_FAILURE: " + serviceLogFailurePrefix

        print(f'{serviceLogFailurePrefix}email:{email}, organization:{organization}, function({function.__name__}:{correlation_id}:{client_version}) FAILED with exception: {exception_info}')

        if service_stage in ('prod', 'staging'):
            serviceFailureDetails = "Internal Boost Service error has occurred. Please retry or contact Polyverse Boost Support if the error continues"

        elif service_stage in ('dev', "test", "local"):
            serviceFailureDetails = exception_info

        if cloudwatch is not None:
            subsegment = xray_recorder.begin_subsegment('exception')
            subsegment.put_annotation('correlation_id', correlation_id)
            subsegment.put_annotation('error', exception_info)
            xray_recorder.end_subsegment()

        status_code = getattr(e, 'STATUS_CODE', 500)

        account = clean_account(account, email, organization)

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': api_version},
            'body': json.dumps({
                "error": serviceFailureDetails,
                'account': account
            }),
        }

    result['account'] = clean_account(account)
    # Put this into a JSON object - assuming the result is already an object
    json_obj = result

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': api_version},
        'body': json.dumps(json_obj),
    }
