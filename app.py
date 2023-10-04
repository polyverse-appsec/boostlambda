from chalice import Chalice

from chalicelib.telemetry import cloudwatch, xray_recorder
from chalicelib.payments import customer_portal_url, customerportal_api_version
from chalicelib.app_utils import process_request, validate_request_lambda
from chalicelib.auth import fetch_orgs, fetch_email_and_username, extract_client_version, userorganizations_api_version

from chalicelib.processors.FlowDiagramProcessor import FlowDiagramProcessor
from chalicelib.processors.SummaryProcessor import SummarizeProcessor
from chalicelib.processors.ExplainProcessor import ExplainProcessor
from chalicelib.processors.CustomProcessor import CustomProcessor
from chalicelib.processors.GenerateProcessor import GenerateProcessor
from chalicelib.processors.ConvertCodeFunctionProcessor import ConvertCodeFunctionProcessor
from chalicelib.processors.TestGeneratorProcessor import TestGeneratorProcessor
from chalicelib.processors.AnalyzeProcessor import AnalyzeProcessor
from chalicelib.processors.ComplianceProcessor import ComplianceProcessor
from chalicelib.processors.CodingGuidelinesProcessor import CodingGuidelinesProcessor
from chalicelib.processors.BlueprintProcessor import BlueprintProcessor
from chalicelib.processors.SecurityFunctionProcessor import SecurityFunctionProcessor
from chalicelib.processors.ComplianceFunctionProcessor import ComplianceFunctionProcessor
from chalicelib.processors.CompareCodeProcessor import CompareCodeProcessor
from chalicelib.processors.PerformanceProcessor import PerformanceProcessor
from chalicelib.processors.PerformanceFunctionProcessor import PerformanceFunctionProcessor
from chalicelib.processors.QuickBlueprintProcessor import QuickBlueprintProcessor
from chalicelib.processors.DraftBlueprintFunctionProcessor import DraftBlueprintFunctionProcessor
from chalicelib.processors.QuickSummaryProcessor import QuickSummaryProcessor
from chalicelib.processors.CustomScanFunctionProcessor import CustomScanFunctionProcessor
from chalicelib.processors.ChatProcessor import ChatProcessor

import uuid
import json
import time
import traceback


app = Chalice(app_name='boost')

# For future logging purposes, we can use the following:
# https://aws.github.io/chalice/topics/logging.html
# Default logging level is logging.ERROR
# app.log.setLevel(logging.DEBUG)
# app.log.debug("This is a debug statement")
# app.log.error("This is an error statement")

flowDiagramProcessor = FlowDiagramProcessor()


@app.lambda_function(name='flowdiagram')
def flowdiagram(event, _):
    return process_request(event, flowDiagramProcessor.flowdiagram_code, flowDiagramProcessor.api_version)


summarizeProcessor = SummarizeProcessor()


@app.lambda_function(name='summarize')
def summarize(event, _):
    return process_request(event, summarizeProcessor.summarize_inputs, summarizeProcessor.api_version)


explainProcessor = ExplainProcessor()


@app.lambda_function(name='explain')
def explain(event, _):
    return process_request(event, explainProcessor.explain_code, explainProcessor.api_version)


generateProcessor = GenerateProcessor()


@app.lambda_function(name='generate')
def generate(event, _):
    return process_request(event, generateProcessor.convert_code, generateProcessor.api_version)


convertCodeFunctionProcessor = ConvertCodeFunctionProcessor()


@app.lambda_function(name='convert_code')
def convert_code(event, context):
    return process_request(event, convertCodeFunctionProcessor.convert_code, convertCodeFunctionProcessor.api_version)


compareCodeProcessor = CompareCodeProcessor()


@app.lambda_function(name='compare_code')
def compare_code(event, _):
    return process_request(event, compareCodeProcessor.compare_code, compareCodeProcessor.api_version)


testGeneratorProcessor = TestGeneratorProcessor()


@app.lambda_function(name='testgen')
def testgen(event, _):
    return process_request(event, testGeneratorProcessor.testgen_code, testGeneratorProcessor.api_version)


analyzeProcessor = AnalyzeProcessor()


@app.lambda_function(name='analyze')
def analyze(event, _):
    return process_request(event, analyzeProcessor.analyze_code, analyzeProcessor.api_version)


securityFunctionProcessor = SecurityFunctionProcessor()


@app.lambda_function(name='analyze_function')
def analyze_function(event, _):
    return process_request(event, securityFunctionProcessor.secure_code, securityFunctionProcessor.api_version)


complianceProcessor = ComplianceProcessor()


@app.lambda_function(name='compliance')
def compliance(event, context):
    return process_request(event, complianceProcessor.compliance_code, complianceProcessor.api_version)


complianceFunctionProcessor = ComplianceFunctionProcessor()


@app.lambda_function(name='compliance_function')
def compliance_function(event, _):
    return process_request(event, complianceFunctionProcessor.check_compliance, complianceFunctionProcessor.api_version)


codeguidelinesProcessor = CodingGuidelinesProcessor()


@app.lambda_function(name='codeguidelines')
def codeguidelines(event, context):
    return process_request(event, codeguidelinesProcessor.checkguidelines_code, codeguidelinesProcessor.api_version)


performanceProcessor = PerformanceProcessor()


@app.lambda_function(name='performance')
def performance(event, context):
    return process_request(event, performanceProcessor.check_performance, performanceProcessor.api_version)


performanceFunctionProcessor = PerformanceFunctionProcessor()


@app.lambda_function(name='performance_function')
def performance_function(event, context):
    return process_request(event, performanceFunctionProcessor.check_performance, performanceFunctionProcessor.api_version)


customScanFunctionProcessor = CustomScanFunctionProcessor()


@app.lambda_function(name='customscan_function')
def customscan_function(event, context):
    return process_request(event, customScanFunctionProcessor.custom_scan, customScanFunctionProcessor.api_version)


blueprintProcessor = BlueprintProcessor()


@app.lambda_function(name='blueprint')
def blueprint(event, context):
    return process_request(event, blueprintProcessor.blueprint_code, blueprintProcessor.api_version)


quickBlueprintProcessor = QuickBlueprintProcessor()


@app.lambda_function(name='quick-blueprint')
def quick_blueprint(event, context):
    return process_request(event, quickBlueprintProcessor.quick_blueprint, quickBlueprintProcessor.api_version)


quickSummaryProcessor = QuickSummaryProcessor()


@app.lambda_function(name='quick-summary')
def quick_summary(event, context):
    return process_request(event, quickSummaryProcessor.quick_summary, quickSummaryProcessor.api_version)


draftBlueprintFunctionProcessor = DraftBlueprintFunctionProcessor()


@app.lambda_function(name='draft-blueprint')
def draft_blueprint(event, context):
    return process_request(event, draftBlueprintFunctionProcessor.draft_blueprint, draftBlueprintFunctionProcessor.api_version)


chatProcessor = ChatProcessor()


@app.lambda_function(name='chat')
def chatprocess(event, _):
    return process_request(event, chatProcessor.process_chat, chatProcessor.api_version)


customProcessor = CustomProcessor()


@app.lambda_function(name='customprocess')
def customprocess(event, _):
    return process_request(event, customProcessor.customprocess_code, customProcessor.api_version)


@xray_recorder.capture('customer_portal')
@app.lambda_function(name='customer_portal')
def customer_portal(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)
    email = "unknown"  # in case we fail early and don't get the email address
    organization = "unknown"
    function_name = context.function_name

    print(f'Inbound request {correlation_id} {function_name}')

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
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
        # If cw_client has been set, use xray_recorder.capture
        if cloudwatch is not None:
            with xray_recorder.capture('validate_request_lambda'):
                account = validate_request_lambda(json_data, function_name, correlation_id, False)
        else:
            # Otherwise, call the function directly
            start_time = time.monotonic()
            account = validate_request_lambda(json_data, function_name, correlation_id, False)
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} validate_request: {end_time - start_time:.3f} seconds')

        if 'email' in account:
            email = account['email']

        if not account['enabled'] and account['status'] not in ('suspended', 'expired'):
            status = account['status']
            session = None
            print(f'{status}: email:{email}, organization:{organization}, function({function_name}:{correlation_id}:{client_version}) No Customer Portal generated')
        else:
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

        print(f'BOOST_USAGE: email:{email}, organization:{organization}, function({function_name}:{correlation_id}:{client_version}) SUCCEEDED')

    except Exception as e:
        exception_info = traceback.format_exc().replace('\n', ' ')
        # Record the error and return as HTTP result
        print(f'BOOST_USAGE: email:{email}, organization:{organization}, function({function_name}:{correlation_id}:{client_version}) FAILED with exception: {exception_info}')
        if cloudwatch is not None:
            subsegment = xray_recorder.begin_subsegment('exception')
            subsegment.put_annotation('correlation_id', correlation_id)
            subsegment.put_annotation('error', exception_info)
            xray_recorder.end_subsegment()

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

    del account['customer']
    del account['subscription']
    del account['subscription_item']

    if session is None:
        account["portal_url"] = None

    # if this user is NOT the owner of the account, don't provide an account mgmt uri
    elif account["email"] != account["owner"]:
        # allow any polyverse user to access polyverse account data
        if account["email"].endswith(("@polyverse.io", "@polytest.ai", "@polyverse.com")):
            account["portal_url"] = session.url
        else:
            account["portal_url"] = None

    else:
        account["portal_url"] = session.url

    # Now return the json object in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json',
                    'X-API-Version': customerportal_api_version},
        'body': json.dumps(account)
    }


@xray_recorder.capture('user_organizations')
@app.lambda_function(name='user_organizations')
def user_organizations(event, context):

    # Generate a new UUID for the correlation ID
    correlation_id = str(uuid.uuid4())
    print("correlation_id is: " + correlation_id)
    email = "unknown"  # in case we fail early and don't get the email address
    organizations = "UNKNOWN"
    function_name = context.function_name

    print(f'Inbound request {correlation_id} {function_name}')

    try:
        # Extract parameters from the event object
        if 'body' in event:
            # event body is a string, so parse it as JSON
            json_data = json.loads(event['body'])
        else:
            json_data = event

        client_version = extract_client_version(event)
        if ('version' not in json_data):
            json_data['version'] = client_version
        else:
            client_version = json_data['version']

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

        if orgs is None:
            organizations = "NONE FOUND"
        else:
            organizations = ','.join(orgs)
            organizations = f"({organizations})"

        print(f'BOOST_USAGE: email:{email}, organization:{organizations}, function({function_name}:{correlation_id}:{client_version}) SUCCEEDED')

    except Exception as e:
        exception_info = traceback.format_exc().replace('\n', ' ')
        # Record the error and return as HTTP result
        print(f'BOOST_USAGE: email:{email}, organization:{organizations}, function({function_name}:{correlation_id}:{client_version}) FAILED with exception: {exception_info}')
        if cloudwatch is not None:
            subsegment = xray_recorder.begin_subsegment('exception')
            subsegment.put_annotation('correlation_id', correlation_id)
            subsegment.put_annotation('error', exception_info)
            xray_recorder.end_subsegment()

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
