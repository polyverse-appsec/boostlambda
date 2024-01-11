from chalice.test import Client
import jwt
import time
import boto3
from app import app
import json
from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


def get_private_key():

    secret_name = "boost-sara/sara-client-private-key"
    region_name = "us-west-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )

    # Decrypts secret using the associated KMS key.
    private_key = get_secret_value_response['SecretString']

    return private_key


def get_signed_headers(email, org):

    private_key = get_private_key()

    # create an unsigned object that expires in 2 mins to allow for tests to run seconds from now (unix system time + 60 seconds)
    expiration_unix_time = int(time.time()) + 120

    # create an unsigned object that expires in 15 seconds from now (unix system time + 15 seconds)
    unsigned_identity = {
        "email": email,
        "organization": org,
        "expires": expiration_unix_time
    }

    # Create the JWT token
    signed_identity = jwt.encode(unsigned_identity, private_key, algorithm='RS256')

    signed_headers = {'x-signed-identity': signed_identity}

    return signed_headers


def test_strong_authn():
    email = "unittest@polytest.ai"
    org = "polytest.ai"

    print("Running test: Strong authentication")

    signed_headers = get_signed_headers(email, org)

    with Client(app) as client:
        request_body = signed_headers

        response = client.lambda_.invoke(
            'customer_portal', request_body)

        assert response.payload['statusCode'] == 200

        body = json.loads(response.payload['body'])
        assert body['status'] == 'premium'
        assert body['portal_url'] is not None
        assert body['enabled'] is True


# test the customer portal with a valid email address
def test_customer_portal_registered():
    with Client(app) as client:
        request_body = {
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'customer_portal', request_body)

        assert response.payload['statusCode'] == 200

        body = json.loads(response.payload['body'])
        assert body['status'] == 'paid'
        assert body['portal_url'] is not None
        assert body['enabled'] is True


# test the customer portal with an invalid session
def test_customer_portal_unregistered():
    with Client(app) as client:
        request_body = {
            'session': 'testemail: foo@bar.com',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'customer_portal', request_body)

        assert response.payload['statusCode'] == 200
        body = json.loads(response.payload['body'])
        assert body['status'] == 'unregistered'
        assert body['portal_url'] is None
        assert body['enabled'] is False


# test the customer portal with an invalid session
def test_customer_portal_unregistered_no_org():
    with Client(app) as client:
        request_body = {
            'session': 'testemail: foo@bar.com',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'customer_portal', request_body)

        assert response.payload['statusCode'] == 200
        body = json.loads(response.payload['body'])
        assert body['status'] == 'unregistered'
        assert body['portal_url'] is None
        assert body['enabled'] is False


# test the customer portal with an invalid session
def test_customer_portal_unauthorized_no_session():
    with Client(app) as client:

        request_body = {
        }

        response = client.lambda_.invoke(
            'customer_portal', request_body)

        assert response.payload['statusCode'] == 401
