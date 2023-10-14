import json
import boto3
import os
from botocore.exceptions import ClientError, EndpointConnectionError

secret_json = None


def get_secrets(stage='prod'):
    global secret_json
    if secret_json is not None:
        return secret_json

    secret_name = "exetokendev"
    region_name = "us-west-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except EndpointConnectionError as e:
        raise e
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    awssecret = get_secret_value_response['SecretString']

    secret_json = json.loads(awssecret)
    # Use the get() method to retrieve the value of CHALICE_STAGE, with a default value of 'dev'
    chalice_stage = os.environ.get('CHALICE_STAGE', stage)

    # Use the retrieved value in the conditional statement
    if chalice_stage == 'prod':
        secret_json['stripe'] = secret_json['stripe_prod']
    else:
        secret_json['stripe'] = secret_json['stripe_dev']

    return secret_json
