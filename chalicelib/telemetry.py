import decimal
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import boto3
import os
import traceback


# If running under AWS Lambda - Patch all supported libraries for X-Ray tracing, enable CloudWatch
if 'AWS_CHALICE_CLI_MODE' not in os.environ and 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    print('AWS Lambda Enabled: Setting up Telemetry, Tracing and CloudWatch')
    patch_all()
    print('patched all functions')
    # Create a CloudWatch client to log metrics and errors
    cloudwatch = boto3.client('cloudwatch')
    print('CloudWatch enabled')

    xray_recorder.configure(service='Boost', context_missing='LOG_ERROR')
    print('X-Ray configured')
else:
    cloudwatch = None
    print('AWS Lambda not detected, skipping X-Ray configuration.')


class InfoMetrics:
    GITHUB_ACCESS_NOT_FOUND = 'GitHubAccessNotFound'
    BILLING_USAGE_FAILURE = 'BillingUsageFailure'
    OPENAI_RATE_LIMIT = 'OpenAIRateLimit'
    NEW_CUSTOMER = 'NewCustomer'
    NEW_CUSTOMER_ERROR = 'NewCustomerERROR'


class CostMetrics:
    RESPONSE_SIZE = 'ResponseSize'
    PROMPT_SIZE = 'PromptSize'
    OPENAI_COST = 'OpenAICost'
    LOST_BOOST_COST = 'LostBoostCost'
    BOOST_COST = 'BoostCost'
    OPENAI_INPUT_COST = 'OpenAIInputCost'
    OPENAI_CUSTOMERINPUT_COST = 'OpenAICustomerInputCost'
    OPENAI_OUTPUT_COST = 'OpenAIOutputCost'
    OPENAI_TOKENS = 'OpenAITokens'
    OPENAI_INPUT_TOKENS = 'OpenAIInputTokens'
    OPENAI_CUSTOMERINPUT_TOKENS = 'OpenAICustomerInputTokens'
    OPENAI_OUTPUT_TOKENS = 'OpenAIOutputTokens'


# Capture a metric to CloudWatch or local console
# Usage: capture_metric(customer, email, function_name, correlation_id, {'name': 'PromptSize', 'value': prompt_size, 'unit': 'Bytes'})
# Customer is a dictionary of customer data from the billing database
# metrics is a list of dicts with name, value and unit
# unit: Seconds, Microseconds, Milliseconds, Bytes, Kilobytes, Megabytes, Gigabytes, Terabytes, Bits, Kilobits, Megabits, Gigabits, Terabits, Percent, Count, Count/Second, None
def capture_metric(customer, email, function_name: "capture_metric", correlation_id, *metrics):
    try:
        if cloudwatch is not None:
            lambda_function = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', function_name)
            metric_data = []
            for metric in metrics:
                metric_obj = {
                    'MetricName': metric['name'],
                    'Dimensions': [
                        {
                            'Name': 'Customer',
                            'Value': customer['name']
                        },
                        {
                            'Name': 'AccountID',
                            'Value': customer['id']
                        },
                        {
                            'Name': 'UserEmail',
                            'Value': email
                        },
                        {
                            'Name': 'LambdaFunctionName',
                            'Value': lambda_function
                        },
                        {
                            'Name': 'CorrelationID',
                            'Value': correlation_id
                        }
                    ],
                    'Unit': metric['unit'],
                    'Value': metric['value'],
                    'StorageResolution': 1  # Note that this is 1-second resolution, may be too high
                }
                metric_data.append(metric_obj)
            cloudwatch.put_metric_data(Namespace='Boost/Lambda', MetricData=metric_data)
        else:
            for metric in metrics:
                if isinstance(metric['value'], float) or isinstance(metric['value'], decimal.Decimal):
                    formatted_value = f"{metric['value']:.5f}"
                else:
                    formatted_value = str(metric['value'])
                print(f"METRIC::[{customer['name']}:{customer['id']}:{email}]{function_name}({correlation_id}):{metric['name']}: {formatted_value} ({metric['unit']})")

    # Never fail on metrics
    except Exception:
        exception_info = traceback.format_exc().replace('\n', ' ')
        print(f"capture_metric:FAILED:ERROR: Failed to capture metric: {exception_info}")
