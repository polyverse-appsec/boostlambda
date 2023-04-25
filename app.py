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

app = Chalice(app_name='boost')


@app.lambda_function(name='explain')
def explain(event, context):
    # print the event and context objects
    print("event is: " + str(event))
    print("context is: " + str(context))

    try:
        # Extract parameters from the event object
        # if the event object has a body, use that, otherwise use the event object itself
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

        # Extract the code from the json data
        code = json_data.get('code')

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to explain")

        # Now call the explain function
        explanation = explain_code(code)

        print("explained code is: " + explanation)

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

    except Exception as e:
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


@app.lambda_function(name='generate')
def generate(event, context):
    try:
        # Extract parameters from the event object
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

        # Parse the request body as JSON
        print("got to generate with ")
        print(json_data)

        # Extract the explanation and original_code from the json data
        explanation = json_data.get('explanation')
        if explanation is None:
            raise BadRequestError("Error: please provide the initial code explanation")

        original_code = json_data.get('originalCode')
        if original_code is None:
            raise BadRequestError("Error: please provide the original code")

        # The output language is optional; if not set, then default to Python
        outputlanguage = json_data.get('language', 'python')

        # Now call the explain function
        code = generate_code(explanation, original_code, outputlanguage)

        print("generated code is: " + code)

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

    except Exception as e:
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


@app.lambda_function(name='testgen')
def testgen(event, context):
    try:
        # Extract parameters from the event object

        # event body is a string, so parse it as JSON
        if 'body' in event:
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

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

        testcode = testgen_code(code, outputlanguage, framework)

        json_obj = {}
        json_obj["testcode"] = testcode

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json',
                        'X-API-Version': testgen_api_version},
            'body': json.dumps(json_obj)
        }

    except Exception as e:
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


@app.lambda_function(name='analyze')
def analyze(event, context):
    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

        # Extract the code from the json data
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze")

        # Now call the explain function
        analysis = analyze_code(code)

        print("analyzed code is: " + analysis)

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

    except Exception as e:
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


@app.lambda_function(name='compliance')
def compliance(event, context):
    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

        # Extract the code from the json data
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for compliance")

        # Now call the explain function
        analysis = compliance_code(code)

        print("compliance analyzed code is: " + analysis)

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

    except Exception as e:
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


@app.lambda_function(name='codeguidelines')
def codeguidelines(event, context):
    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

        # Extract the code from the json data
        code = json_data['code']

        if code is None:
            raise BadRequestError("Error: please provide a code fragment to analyze for coding guidelines")

        # Now call the explain function
        analysis = guidelines_code(code)

        print("coding guidelines analyzed code is: " + analysis)

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

    except Exception as e:
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


@app.lambda_function(name='blueprint')
def blueprint(event, context):
    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        validate_request_lambda(json_data['session'])

        # Extract the code from the json data
        if 'code' not in json_data:
            raise BadRequestError("Error: please provide a code fragment to blueprint")
        code = json_data['code']
        if code is None:
            raise BadRequestError("Error: please provide a code fragment to blueprint")

        # Extract the prior blueprint from the json data
        if 'blueprint' in json_data:
            prior_blueprint = json_data['blueprint']
            if prior_blueprint is not None:
                print("Prior blueprint: " + prior_blueprint)

        # Now call the explain function
        blueprint = blueprint_code(json_data)

        print("blueprinted code is: " + code)
        print("new blueprint is: " + blueprint)

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

    except Exception as e:
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
