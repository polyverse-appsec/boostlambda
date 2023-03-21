import json
import boto3
from botocore.exceptions import ClientError

secret_json = None

def get_secrets():
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
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    awssecret = get_secret_value_response['SecretString']

    secret_json = json.loads(awssecret)

    return secret_json
