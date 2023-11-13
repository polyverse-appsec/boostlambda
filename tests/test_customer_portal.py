from chalice.test import Client
from app import app
import json
from .test_version import client_version
from . import test_utils  # noqa pylint: disable=unused-import


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
