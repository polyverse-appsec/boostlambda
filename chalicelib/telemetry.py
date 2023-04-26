from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import boto3
import os

# If running under AWS Lambda - Patch all supported libraries for X-Ray tracing, enable CloudWatch
if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    print('AWS Lambda Enabled: Setting up Telemetry, Tracing and CloudWatch')
    xray_recorder.configure(service='Boost', context_missing='LOG_ERROR')
    print('X-Ray configured')
    patch_all()
    print('patched all functions')
    # Create a CloudWatch client to log metrics and errors
    cw_client = boto3.client('cloudwatch')
    print('CloudWatch enabled')
else:
    cw_client = None
    print('AWS Lambda not detected, skipping X-Ray configuration.')
