import traceback
from chalice import Chalice
from chalicelib.auth import validate_request_lambda
from chalice import BadRequestError
from chalicelib.analyze import analyze_code, analyze_api_version
from chalicelib.testgen import testgen_code, testgen_api_version
from chalicelib.compliance import compliance_code, compliance_api_version
from chalicelib.codeguidelines import guidelines_code, guidelines_api_version
from chalicelib.customprocess import customprocess_code, customprocess_api_version
from chalicelib.blueprint import blueprint_code, blueprint_api_version
from chalicelib.convert import explain_code, generate_code, convert_api_version, explain_api_version
from chalicelib.payments import customer_portal_url, customerportal_api_version
from chalicelib.auth import fetch_orgs, fetch_email_and_username, userorganizations_api_version
from chalicelib.flowdiagram import FlowDiagramProcessor

import json
import uuid
from chalicelib.telemetry import cloudwatch, xray_recorder
import time

app = Chalice(app_name='boost')


def process_request(event, context, function, api_version):
    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Now call the function
        if cloudwatch is not None:
            with xray_recorder.capture(function.__name__):
                result = function(json_data, account, context, correlation_id)
        else:
            start_time = time.monotonic()
            result = function(json_data, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} {function.__name__}: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        print(f"{function.__name__} {correlation_id} failed with exception: {exception_info}")
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        status_code = getattr(e, 'STATUS_CODE', 500)

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': api_version},
            'body': json.dumps({"error": str(e)})
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': api_version},
        'body': json.dumps(result)
    }

@app.lambda_function(name='flowdiagram')
def flowdiagram(event, context):
    processor = FlowDiagramProcessor()
    return process_request(event, context, processor.flowdiagram_code, processor.api_version)


@app.lambda_function(name='explain')
def explain(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        # if the event object has a body, use that, otherwise use the event object itself
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data.get('code')
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to explain")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the explain function
        if cloudwatch is not None:
            with xray_recorder.capture('explain_code'):
                explanation = explain_code(code, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            explanation = explain_code(code, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} explain_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("explain {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': explain_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a JSON object
    json_obj = {}
    json_obj["explanation"] = explanation

    # Now return the JSON object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': explain_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='generate')
def generate(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Extract the explanation and original_code from the json data
        explanation = json_data.get('explanation')
        if explanation is None:
            raise BadRequestError("Error: please provide the initial code explanation")

        original_code = json_data.get('originalCode')
        if original_code is None:
            raise BadRequestError("Error: please provide the original code")

        # The output language is optional; if not set, then default to Python
        outputlanguage = json_data.get('language', 'python')

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('generate_code'):
                code = generate_code(explanation, original_code, outputlanguage, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            code = generate_code(explanation, original_code, outputlanguage, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} generate_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("generate {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': convert_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a JSON object
    json_obj = {}
    json_obj["code"] = code

    # Now return the JSON object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': convert_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='testgen')
def testgen(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object

        # event body is a string, so parse it as JSON
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide the code to write tests for")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        language = json_data['language']
        outputlanguage = language
        if outputlanguage is None:
            outputlanguage = "python"

        framework = json_data['framework']
        if framework is None:
            if outputlanguage == "python":
                framework = "pytest"
            else:
                framework = "the best framework for " + outputlanguage + " tests"

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('testgen_code'):
                testcode = testgen_code(code, outputlanguage, framework, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            testcode = testgen_code(code, outputlanguage, framework, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} testgen_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("testgen {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': testgen_api_version},
            'body': json.dumps({"error": str(e)})
        }

    json_obj = {}
    json_obj["testcode"] = testcode

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': testgen_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='analyze')
def analyze(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('analyze_code'):
                analysis = analyze_code(code, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = analyze_code(code, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} analyze_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("analyze {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': analyze_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a json object
    json_obj = {}
    json_obj["analysis"] = analysis

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': analyze_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='compliance')
def compliance(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for compliance")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('compliance_code'):
                analysis = compliance_code(code, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = compliance_code(json_data, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} compliance_code: {end_time - start_time:.3f} seconds')
    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("compliance {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': compliance_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a json object
    json_obj = {}
    json_obj["analysis"] = analysis

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': compliance_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='codeguidelines')
def codeguidelines(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for coding guidelines")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('guidelines_code'):
                analysis = guidelines_code(code, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = guidelines_code(code, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} guidelines_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("codeguidelines {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': guidelines_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a json object
    json_obj = {}
    json_obj["analysis"] = analysis

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': guidelines_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='blueprint')
def blueprint(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        if 'code' not in json_data:
            raise BadRequestError("Error: please provide a code fragment to blueprint")
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to blueprint")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('blueprint_code'):
                blueprint = blueprint_code(json_data, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            blueprint = blueprint_code(json_data, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} blueprint_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("blueprint {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': blueprint_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a json object
    json_obj = {}
    json_obj["blueprint"] = blueprint

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': blueprint_api_version},
        'body': json.dumps(json_obj)
    }


@app.lambda_function(name='customprocess')
def customprocess(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validated, account = validate_request_lambda(json_data, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for coding guidelines")

        # Extract the prompt from the json data
        prompt = json_data['prompt']
        if prompt is None:
            raise BadRequestError("Error: please provide a custom prompt to run against the code fragment")

        email = account['email']
        if email is None:
            raise BadRequestError("Error: Unable to determine email address for account")

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('guidelines_code'):
                analysis = customprocess_code(code, prompt, account, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = customprocess_code(code, prompt, account, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} customProcess_code: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("customprocess {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': customprocess_api_version},
            'body': json.dumps({"error": str(e)})
        }

    # Put this into a json object
    json_obj = {}
    json_obj["analysis"] = analysis

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': customprocess_api_version},
        'body': json.dumps(json_obj)
    }


@xray_recorder.capture('customer_portal')
@app.lambda_function(name='customer_portal')
def customer_portal(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validated, account = validate_request_lambda(json_data, context, correlation_id, False)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            _, account = validate_request_lambda(json_data, context, correlation_id, False)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Now call the openai function
        if cloudwatch is not None:
            with xray_recorder.capture('customer_portal'):
                session = customer_portal_url(account)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            session = customer_portal_url(account)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} portal: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("CustomerPortal {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            document = xray_recorder.current_segment()
            document.put_annotation('correlation_id', correlation_id)
            document.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': customerportal_api_version},
            'body': json.dumps({"error": str(e)})
        }

    json_obj = {}
    json_obj["portal_url"] = session.url
    json_obj["status"] = account['status']

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': customerportal_api_version},
        'body': json.dumps(json_obj)
    }


@xray_recorder.capture('user_organizations')
@app.lambda_function(name='user_organizations')
def user_organizations(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        # Capture the duration of the validation step
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('get_user_organizations'):
                orgs = fetch_orgs(json_data["session"])
                email, username = fetch_email_and_username(json_data["session"])
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            orgs = fetch_orgs(json_data["session"])
            email, username = fetch_email_and_username(json_data["session"])
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

    except Exception as e:
        exception_info = traceback.format_exc()
        # Record the error and re-raise the exception
        print("user_organizations {} failed with exception: {}".format(correlation_id, exception_info))
        if cloudwatch is not None:
            xray_recorder.put_annotation('correlation_id', correlation_id)
            xray_recorder.put_annotation('error', exception_info)

        # if e has a status code, use it, otherwise use 500
        if hasattr(e, 'STATUS_CODE'):
            status_code = e.STATUS_CODE
        else:
            status_code = 500

        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': userorganizations_api_version},
            'body': json.dumps({"error": str(e)})
        }

    json_obj = {}
    json_obj["organizations"] = orgs
    json_obj["email"] = email
    json_obj["personal"] = username

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': userorganizations_api_version},
        'body': json.dumps(json_obj)
    }
