
import traceback
import json
import uuid
import time
import os

from json.decoder import JSONDecodeError

from chalice import BadRequestError
from chalicelib.log import mins_and_secs

from chalicelib.telemetry import cloudwatch, xray_recorder
from chalicelib.auth import \
    validate_request_lambda, \
    clean_account, \
    extract_client_version

from chalicelib.aws import \
    init_current_lambda_cost


def generate_correlation_id():
    correlation_id = str(uuid.uuid4())

    print("correlation_id is: " + correlation_id)

    return correlation_id


def handle_exception(e, correlation_id, email, organization, function_name, api_version):
    exception_info = traceback.format_exc().replace('\n', ' ')
    print(f'BOOST_USAGE: email:{email}, organization:{organization}, function({function_name}:{correlation_id}) FAILED with exception: {exception_info}')

    if cloudwatch is not None:
        subsegment = xray_recorder.begin_subsegment('exception')
        subsegment.put_annotation('correlation_id', correlation_id)
        subsegment.put_annotation('error', exception_info)
        xray_recorder.end_subsegment()

    status_code = getattr(e, 'STATUS_CODE', 500)
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-API-Version': api_version
        },
        'body': json.dumps({"error": str(e)})
    }


def common_lambda_logic(event, function_name, handler_function, api_version):
    correlation_id = generate_correlation_id()

    print(f'Inbound request {correlation_id} {function_name}')

    if os.environ.get('CHALICE_STAGE', 'local') == 'dev':
        print(f'Request Payload:\n{json.dumps(event)}')

    preflight_response = process_cors_preflight(event)
    if preflight_response:
        return process_response(preflight_response, event, function_name)

    try:
        return process_response(handler_function(event, correlation_id), event, function_name)
    except Exception as e:
        return process_response(handle_exception(e, correlation_id, "unknown", "unknown", function_name, api_version), event, function_name)


def process_request(event, function, api_version):
    # Generate a new UUID for the correlation ID
    correlation_id = generate_correlation_id()

    init_current_lambda_cost(correlation_id)

    email = "unknown"  # in case we fail early and don't get the email address
    organization = "unknown"
    account = None
    client_version = "unknown"

    print(f'Inbound request {correlation_id} {function.__name__}')

    preflight_response = process_cors_preflight(event)
    if preflight_response:
        return process_response(preflight_response, event, function.__name__)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            try:
                if not event.get('body', '').strip():
                    # Handle the case where the body is empty or only contains whitespace
                    raise ValueError("Request body is empty or invalid")

                json_data = json.loads(event['body'])
            except JSONDecodeError as e:
                # dump the full event object (not just the body) to the log
                print(f"Event is: {event}")
                # Handle the case where the body is not valid JSON
                print(f"JSON Decode Error: {e}")

            except ValueError as e:
                # dump the full event object (not just the body) to the log
                print(f"Event is: {event}")

                # Handle the case where the body is empty or not valid JSON
                # Log the error or return a meaningful response
                print(f"Error: {e}")

        else:
            json_data = event
        if 'headers' in event:
            headers = event['headers']
        else:
            headers = event  # we're going to use the same event/body structure if running locally to get the headers

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
                account = validate_request_lambda(json_data, headers, function.__name__, correlation_id, False)

                email = account['email'] if 'email' in account else email

                # if not enabled, then we're going to raise an error
                # note: we could return the error in the account object and save
                # calling validate again, but for now, we're going to keep it simple
                if not (account['enabled'] if 'enabled' in account else False):
                    validate_request_lambda(json_data, headers, function.__name__, correlation_id, True)
        else:
            start_time = time.monotonic()
            account = validate_request_lambda(json_data, headers, function.__name__, correlation_id, False)

            email = account['email'] if 'email' in account else email

            # if not enabled, then we're going to raise an error
            # note: we could return the error in the account object and save
            # calling validate again, but for now, we're going to keep it simple
            if not (account['enabled'] if 'enabled' in account else False):
                try:
                    validate_request_lambda(json_data, headers, function.__name__, correlation_id, True)
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

        if os.environ.get('CHALICE_STAGE', 'local') == 'dev':
            print(f'Incoming Request Data that failed to process:\n{json.dumps(event)}')

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

        return process_response({
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'X-API-Version': api_version
            },
            'body': json.dumps({
                "error": serviceFailureDetails,
                'account': account
            }),
        }, event, function.__name__)

    result['account'] = clean_account(account)
    # Put this into a JSON object - assuming the result is already an object
    json_obj = result

    return process_response({
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'X-API-Version': api_version
        },
        'body': json.dumps(json_obj),
    }, event, function.__name__)


def process_response(response, event, function_name):
    is_browser = is_browser_client(event)
    use_json = supports_json(event)

    response = handle_cors_response(response, event)

    # if client requested JSON, then we're done
    if use_json:
        return response

    # otherwise, if a browser client, then we need to return HTML
    if is_browser:
        wrap_html(response, function_name)

    # default to JSON
    return response


def wrap_html(response, function_name):
    # we're going to wrap the response in HTML so it can be rendered as a default page in a browser

    # if 'statusCode' is not 200, then the response is an error so we'll make the page title an error
    if response['statusCode'] != 200:
        page_title = 'Error'
    else:
        page_title = 'Polyverse Boost - ' + function_name

    # we also need to change the content-type to text/html
    response['headers']['Content-Type'] = 'text/html'

    htmlBody = response['body']

    current_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # create the HTML code to store in the new response body
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{page_title}</title>
    </head>
    <body>
        <h1>{page_title}: {current_datetime}</h1>
        <pre>{htmlBody}</pre>
    </body>
    </html>
    '''

    # update the response body
    response['body'] = html

    return response


def is_browser_client(event):
    # we're going to look at the user agent to determine if the client is a browser
    # e.g. "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    # We want to support safari, chrome, firefox, edge, and IE11

    if 'headers' not in event:
        return False

    if 'user-agent' in event['headers']:
        user_agent = event['headers']['user-agent']
        if 'Safari' in user_agent:
            return True
        if 'Chrome' in user_agent:
            return True
        if 'Firefox' in user_agent:
            return True
        if 'Edge' in user_agent:
            return True
        if 'Trident' in user_agent:
            return True

    return False


def supports_json(event):
    # we're going to check the 'accept' header in the request
    #    and if it contains 'application/json', then we'll return JSON
    # e.g. "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

    if 'headers' not in event:
        return False
    elif 'accept' not in event['headers']:
        return False

    if 'application/json' in event['headers']['accept']:
        return True
    elif 'text/json' in event['headers']['accept']:
        return True
    elif 'application/*+json' in event['headers']['accept']:
        return True
    elif 'application/vnd.api+json' in event['headers']['accept']:
        return True
    elif '*/*' in event['headers']['accept']:
        # for clients that ask for html or xml by preference we'll send html
        #    even if they technically could support json via the wildcard filter
        if 'text/html' in event['headers']['accept']:
            return False
        elif 'application/xhtml+xml' in event['headers']['accept']:
            return False
        elif 'application/xml' in event['headers']['accept']:
            return False
        return True

    return False


def process_cors_preflight(event):
    """
    Handles CORS preflight requests.
    If the incoming request is an OPTIONS request, returns a response with necessary headers.
    Otherwise, returns None indicating that normal processing should continue.
    """
    if 'requestContext' not in event:
        return None
    elif 'http' not in event['requestContext']:
        return None
    elif 'method' not in event['requestContext']['http']:
        return None

    if event['requestContext']['http']['method'] == 'OPTIONS':
        print("CORS preflight request received")
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, User-Agent'
            },
            'body': json.dumps({"message": "CORS preflight response"})
        }
    else:
        return None


def handle_cors_response(response, event):
    """
    Handles CORS response.
    If the incoming request has an ORIGIN header, we need to make sure the response
    includes the allow response.
    """

    # only process responses that had CORS or similar headers
    if 'headers' not in event:
        return response

    # Check for Origin in the request headers
    origin = event['headers'].get('Origin', event['headers'].get('origin', '*'))
    response['headers']['Access-Control-Allow-Origin'] = origin

    if os.environ.get('CHALICE_STAGE', 'local') == 'dev':
        print('CORS-enabled Response')

    return response
