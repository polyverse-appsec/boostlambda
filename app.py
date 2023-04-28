from chalice import Chalice
from chalicelib.auth import validate_request_lambda
from chalice import BadRequestError
from chalicelib.analyze import analyze_code, analyze_api_version
from chalicelib.testgen import testgen_code, testgen_api_version
from chalicelib.compliance import compliance_code, compliance_api_version
from chalicelib.codeguidelines import guidelines_code, guidelines_api_version
from chalicelib.blueprint import blueprint_code, blueprint_api_version
from chalicelib.convert import explain_code, generate_code, convert_api_version, explain_api_version

import json
import uuid
from chalicelib.telemetry import cw_client, xray_recorder
import time

app = Chalice(app_name='boost')


@xray_recorder.capture('explain')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data.get('code')

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to explain")

        # Now call the explain function
        if cw_client is not None:
            with xray_recorder.capture('explain_code'):
                explanation = explain_code(code, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            explanation = explain_code(code, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} explain_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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


@xray_recorder.capture('generate')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

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
        if cw_client is not None:
            with xray_recorder.capture('generate_code'):
                code = generate_code(explanation, original_code, outputlanguage, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            code = generate_code(explanation, original_code, outputlanguage, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} generate_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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


@xray_recorder.capture('testgen')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        language = json_data['language']
        framework = json_data['framework']
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide the code to write tests for")

        outputlanguage = language
        if outputlanguage is None:
            outputlanguage = "python"

        if framework is None:
            if outputlanguage == "python":
                framework = "pytest"
            else:
                framework = "the best framework for " + outputlanguage + " tests"

        # Now call the openai function
        if cw_client is not None:
            with xray_recorder.capture('testgen_code'):
                testcode = testgen_code(code, outputlanguage, framework, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            testcode = testgen_code(code, outputlanguage, framework, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} testgen_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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


@xray_recorder.capture('analyze')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        # Now call the openai function
        if cw_client is not None:
            with xray_recorder.capture('analyze_code'):
                analysis = analyze_code(code, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = analyze_code(code, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} analyze_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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


@xray_recorder.capture('compliance')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for compliance")

        # Now call the openai function
        if cw_client is not None:
            with xray_recorder.capture('compliance_code'):
                analysis = compliance_code(code, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = compliance_code(json_data, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} compliance_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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


@xray_recorder.capture('codeguidelines')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for coding guidelines")

        # Now call the openai function
        if cw_client is not None:
            with xray_recorder.capture('guidelines_code'):
                analysis = guidelines_code(code, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            analysis = guidelines_code(code, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} guidelines_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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


@xray_recorder.capture('blueprint')
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
        if cw_client is not None:
            with xray_recorder.capture('validate_request_lambda'):
                validate_request_lambda(json_data, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            validate_request_lambda(json_data, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        # Extract the code from the json data
        if 'code' not in json_data:
            raise BadRequestError("Error: please provide a code fragment to blueprint")
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to blueprint")

        # Now call the openai function
        if cw_client is not None:
            with xray_recorder.capture('blueprint_code'):
                blueprint = blueprint_code(json_data, event, context, correlation_id)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            blueprint = blueprint_code(json_data, event, context, correlation_id)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} blueprint_code: {end_time - start_time:.3f} seconds')

    except Exception as e:

        # Record the error and re-raise the exception
        if cw_client is not None:
            xray_recorder.capture('exception', name='error', attributes={'correlation_id': correlation_id})
        else:
            print("Explain {} failed with exception: {}".format(correlation_id, e))

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
