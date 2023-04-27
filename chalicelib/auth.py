import requests
import shopify
from . import pvsecret
from chalice import UnauthorizedError
import re
from chalicelib.telemetry import cw_client, xray_recorder
import time


def fetch_email(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }
    url = 'https://api.github.com/user/emails'

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        emails = response.json()
        for email in emails:
            if email['primary']:
                return email['email']
    else:
        email_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(email_pattern, access_token)

        if match:
            return match.group(1)
        return None


# function to get the domain from an email address, returns true if validated, and returns email if found in token
def validate_github_session(access_token, correlation_id):
    if cw_client is not None:
        with xray_recorder.capture('github_verify_email'):
            email = fetch_email(access_token)
    else:
        start_time = time.monotonic()
        email = fetch_email(access_token)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} github_verify_email: {end_time - start_time:.3f} seconds')

    print('BOOST_USAGE: email is ', email)

    if email:

        if cw_client is not None:
            with xray_recorder.capture('shopify_verify_email'):
                return verify_email_with_shopify(email, correlation_id), email
        else:
            start_time = time.monotonic()
            verified = verify_email_with_shopify(email, correlation_id), email
            end_time = time.monotonic()
            print(f'Execution time {correlation_id} shopify_verify_email: {end_time - start_time:.3f} seconds')
            return verified

    else:
        return False, email


def verify_email_with_shopify(email, correlation_id):
    # Authenticate with the Shopify API
    shop_url = 'https://polyverse-security.myshopify.com/admin/api/2023-01'
    api_version = '2023-01'
    secret_json = pvsecret.get_secrets()

    shopify_token = secret_json["shopify"]

    session = shopify.Session(shop_url, api_version, shopify_token)
    shopify.ShopifyResource.activate_session(session)

    shopify.ShopifyResource.set_site(shop_url)

    # Fetch the customer information using the email address
    # first see if the email is in a valid domain
    domain = get_domain(email)
    if is_valid_domain(domain):
        customers = shopify.Customer.search(query=f'email:*@{domain}')
    else:
        customers = shopify.Customer.find(email=email)

    # Clear the Shopify API session
    shopify.ShopifyResource.clear_session()

    # Check if a customer was found
    # Check if any customers were found
    if customers:
        # Loop through the customers and print their information
        for customer in customers:
            # Only print customer info if locally debugging - until we enable aggressive short-duration log collection for debugging (CloudWatch)
            # avoid logging anything except email to avoid any unnecessary PII concerns
            if cw_client is None:
                print(f"Customer Information for {customer.email}:")
                print(f"ID: {customer.id}")
                print(f"First Name: {customer.first_name}")
                print(f"Last Name: {customer.last_name}")
                print(f"Total Spent: {customer.total_spent} {customer.currency}")
                print(f"Orders Count: {customer.orders_count}")
            if customer.orders_count > 0:
                return True
    else:
        if (cw_client is not None):
            if customer is None:
                # Send a CloudWatch alert
                cw_client.put_metric_data(
                    Namespace='Boost/Lambda',
                    MetricData=[
                        {
                            'MetricName': 'CustomerNotFound',
                            'Dimensions': [
                                {
                                    'Name': 'Application',
                                    'Value': 'Boost'
                                },
                                {
                                    'Name': 'CorrelationID',
                                    'Value': correlation_id
                                },
                                {
                                    'Name': 'CustomerEmail',
                                    'Value': email
                                }
                            ],
                            'Value': 1,
                            'Unit': 'Count',
                            'StorageResolution': 60
                        }
                    ]
                )
        else:
            print(f"No customer found with email {email}")

    return email.endswith('@polyverse.com') or email.endswith('@polyverse.io')


# function to validate that the request came from a github logged in user or we are running on localhost
# or that the session token is valid github oauth token for a subscribed email
def validate_request(request, correlation_id):

    # otherwise check to see if we have a valid github session token
    # parse the request body as json
    try:
        json_data = request.json_body
        # extract the code from the json data
        session = json_data.get('session')
        validate = validate_github_session(session, correlation_id)
        if (validate):
            return True, None
    except ValueError:
        # don't do anything if the json is invalid
        pass

    # last chance, check the ip address

    # if we don't have a rapid api key, check the origin
    # ip = request.context["identity"]["sourceIp"]
    # print("got client ip: " + ip)
    # if the ip starts with 127, it's local
    # if ip.startswith("127"):
    #    return True, None

    # if we got here, we failed, return an error
    raise UnauthorizedError("Error: please login to github to use this service")


# function to validate that the request came from a github logged in user or we are running on localhost
# or that the session token is valid github oauth token for a subscribed email. This version is for the
# raw lambda function and so has the session key passed in as a string
def validate_request_lambda(session, correlation_id):

    # otherwise check to see if we have a valid github session token
    # parse the request body as json
    try:
        # extract the code from the json data
        validated, email = validate_github_session(session, correlation_id)
        if validated:
            return True
    except ValueError:
        # don't do anything if the json is invalid
        pass

    # last chance, check the ip address

    # if we don't have a rapid api key, check the origin
    # ip = request.context["identity"]["sourceIp"]
    # print("got client ip: " + ip)
    # if the ip starts with 127, it's local
    # if ip.startswith("127"):
    #    return True, None

    if (cw_client is not None):
        # Send a CloudWatch alert
        cw_client.put_metric_data(
            Namespace='Boost/Lambda',
            MetricData=[
                {
                    'MetricName': 'GitHubAccessNotFound',
                    'Dimensions': [
                        {
                            'Name': 'Application',
                            'Value': 'Boost'
                        },
                        {
                            'Name': 'CustomerEmail',
                            'Value': email
                        },
                        {
                            'Name': 'CorrelationID',
                            'Value': correlation_id
                        }
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'StorageResolution': 60
                }
            ]
        )
    else:
        print("Failed to validate GitHub / Access token")

    # if we got here, we failed, return an error
    raise UnauthorizedError("Error: please login to github to use this service")


def get_domain(email):
    return email.split('@')[-1].lower()


def is_valid_domain(domain):
    major_email_providers = {
        'gmail.com',
        'yahoo.com',
        'hotmail.com',
        'aol.com',
        'outlook.com',
        'msn.com',
        'live.com',
        'icloud.com',
        'mail.com',
        'comcast.net',
        'verizon.net',
        'sbcglobal.net',
        'ymail.com',
        'me.com'
    }
    return domain not in major_email_providers
