
import traceback
import json
import uuid
import time

from chalice import BadRequestError

from chalicelib.telemetry import cloudwatch, xray_recorder
from chalicelib.auth import validate_request_lambda
from chalicelib.auth import extract_client_version


def process_request(event, function, api_version):
    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)
    email = "unknown"  # in case we fail early and don't get the email address
    organization = "unknown"

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
                _, account = validate_request_lambda(json_data, function.__name__, correlation_id)
        else:
            start_time = time.monotonic()
            _, account = validate_request_lambda(json_data, function.__name__, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        email = account['email']
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
            print(f'Execution time {correlation_id} {function.__name__}: {end_time - start_time:.3f} seconds')

        print(f'BOOST_USAGE: email:{email}, organization:{organization}, function({function.__name__}:{correlation_id}:{client_version}) SUCCEEDED')

    except Exception as e:
        exception_info = traceback.format_exc().replace('\n', ' ')
        print(f'BOOST_USAGE: email:{email}, organization:{organization}, function({function.__name__}:{correlation_id}:{client_version}) FAILED with exception: {exception_info}')
        if cloudwatch is not None:
            subsegment = xray_recorder.begin_subsegment('exception')
            subsegment.put_annotation('correlation_id', correlation_id)
            subsegment.put_annotation('error', exception_info)
            xray_recorder.end_subsegment()

        status_code = getattr(e, 'STATUS_CODE', 500)

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a JSON object - assuming the result is already an object
    json_obj = result

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': api_version},
        'body': json.dumps(json_obj)
    }
