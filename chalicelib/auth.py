import requests
from chalice import UnauthorizedError
import re
from chalicelib.telemetry import cloudwatch, xray_recorder, capture_metric, InfoMetrics
import time
from .payments import check_valid_subscriber, ExtendedAccountBillingError
from chalicelib.version import API_VERSION
from chalicelib.log import mins_and_secs
from cachetools import TTLCache
import random
import jwt
from datetime import datetime
from requests.exceptions import ConnectionError
from chalicelib.pvsecret import get_jwt_signing_key

userorganizations_api_version = API_VERSION  # API version is global for now, not service specific
print("userorganizations_api_version: ", userorganizations_api_version)


class ExtendedUnauthorizedError(UnauthorizedError):
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason


# Create a cache with a time-to-live (TTL) of 5 minutes
token_2_email_cache = TTLCache(maxsize=100, ttl=300)


def request_get_with_retry(url, headers, max_retries=1):
    retry_count = 0

    while retry_count <= max_retries:
        try:
            response = requests.get(url, headers=headers)
            if retry_count > 0:
                print(f"Successful GET to {url}: after attempt {retry_count + 1} retry of {max_retries + 1}")

            return response
        except ConnectionError as e:
            if retry_count < max_retries:
                wait_time = random.randint(3, 5)  # Random wait between 3 to 5 seconds
                time.sleep(wait_time)
                print(f"Connection error occurred retrieving {url}: {str(e)}; attempt {retry_count + 1} of {max_retries + 1} after {mins_and_secs(wait_time)}")
                retry_count += 1
            else:
                print(f"Connection error: {str(e)} Max retries exceeded: {max_retries} retrieving url: {url}... giving up")
                raise e


def fetch_email(access_token):
    # Check if the access token is already cached
    if access_token in token_2_email_cache:
        return token_2_email_cache[access_token]
    else:
        print("Refreshing Email Cache: *access token hidden*")

    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }
    url = 'https://api.github.com/user/emails'

    response = request_get_with_retry(url, headers=headers)

    if response.status_code == 200:
        emails = response.json()
        for email in emails:
            if email['primary']:
                # Cache the access token and its corresponding email
                print(f"Cached GitHub Auth Token: {email['email']}")
                token_2_email_cache[access_token] = email['email']
                return email['email']
    else:
        response_json = response.json()
        if 'message' in response_json and response_json['message'] == 'Not Found':
            error_message = "GitHub email query failed: OAuth token may lack 'read:email' scope or be invalid."
            print(f"ERROR: {error_message}")
            return None

        email_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(email_pattern, access_token)

        if match:
            email = match.group(1)
            # Cache the access token and its corresponding email
            print(f"Cached GitHub Auth Token: {email}")
            token_2_email_cache[access_token] = email
            return email

        print(f"ERROR: GitHub email query failure: {response_json}")
        return None


# Create a cache with a time-to-live (TTL) of 5 minutes
token_2_user_cache = TTLCache(maxsize=100, ttl=300)


def fetch_email_and_username(access_token, raiseOnError=True):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }

    # get email from github
    email = fetch_email(access_token)
    if email is None:
        if raiseOnError:
            raise ExtendedUnauthorizedError("GitHub Email is required to access Boost account")
        else:
            return None, None

    # Check if the username is already cached
    if access_token in token_2_user_cache:
        username = token_2_user_cache[access_token]
        return email, username
    else:
        if access_token in token_2_email_cache:
            print(f"Refreshing User Cache: {token_2_email_cache[access_token]}")
        else:
            print("Refreshing User Cache: *access token hidden*")

    # get login/username from github
    url = 'https://api.github.com/user'
    response = request_get_with_retry(url, headers=headers)

    if response.status_code == 200:
        user = response.json()
        username = user['login']

        # Cache the username for future use
        token_2_user_cache[access_token] = username

        return email, username
    else:
        # if the user is a test user, return the email as the username
        email_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(email_pattern, access_token)

        if match:
            username = match.group(1)

            # Cache the username for future use
            token_2_user_cache[access_token] = username

            return username, username

        # if its not a test user, we've failed to find the user in GitHub
        #     so we don't know if this is a valid user or not
        print(f"ERROR: GitHub User query failure: {response.json()}")
        return None, None


# Create a cache with a time-to-live (TTL) of 5 minutes
token_2_org_cache = TTLCache(maxsize=100, ttl=300)


def fetch_orgs(access_token, requested_organization=None):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }

    # Check if the orgs are already cached for the given access_token
    if access_token in token_2_org_cache:
        return token_2_org_cache[access_token]
    else:
        if access_token in token_2_email_cache:
            print(f"Refreshing Org Cache: {token_2_email_cache[access_token]}")
        else:
            print("Refreshing Org Cache: *access token hidden*")

    url = 'https://api.github.com/user/orgs'
    response = request_get_with_retry(url, headers=headers)
    # if we got a 200, then we have a list of orgs, otherwise check for a testorg
    if response.status_code == 200:
        orgs = response.json()
        # we just need the string of the org name, it's in the 'login' field.  update the orgs array to just be the string
        if isinstance(orgs, list):
            for i in range(len(orgs)):
                orgs[i] = orgs[i]['login']

        # Cache the orgs for future use
        token_2_org_cache[access_token] = orgs

        return orgs
    else:
        org_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(org_pattern, access_token)

        if match:
            email = match.group(1)
            org = get_domain(email) if requested_organization is None else requested_organization
            orgs = [org]

            # Cache the orgs for future use
            token_2_org_cache[access_token] = orgs

            return orgs

        print(f"ERROR: GitHub Org query failure: {response.json()}")

        return None


# function to get the domain from an email address, returns true if validated, and returns email if found in token
def validate_github_session(access_token, organization, correlation_id, raiseOnError=True):
    if cloudwatch is not None:
        with xray_recorder.capture('fetch_email_and_username'):
            email, username = fetch_email_and_username(access_token, raiseOnError)
    else:
        start_time = time.monotonic()
        email, username = fetch_email_and_username(access_token, raiseOnError)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} fetch_email_and_username: {mins_and_secs(end_time - start_time)}')

    if email is None:
        if raiseOnError:
            raise ExtendedUnauthorizedError("GitHub Email is required to access Boost account")
        else:
            return False, None

    # if the username matches the user's requested org, then we'll use a "personal" org
    if username == organization:
        return True, email

    # otherwise, we validate the user's requested organization against their GitHub org list
    if cloudwatch is not None:
        with xray_recorder.capture('fetch_orgs'):
            orgs = fetch_orgs(access_token, organization)
    else:
        start_time = time.monotonic()
        orgs = fetch_orgs(access_token, organization)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} fetch_orgs: {mins_and_secs(end_time - start_time)}')

    # make sure that organization is in the list of orgs, make sure orgs is an array then loop through
    if orgs is not None:
        if isinstance(orgs, list):
            for org in orgs:
                if org == organization:
                    return True, email
        else:
            if orgs == organization:
                return True, email
            else:
                print(f'{correlation_id}:validate_github_session orgs for {email} unexpected: {orgs}')
    else:
        print(f'{correlation_id}:validate_github_session get orgs failed for {email}')

    return False, email


# function to validate that the request came from a github logged in user or we are running on localhost
# or that the session token is valid github oauth token for a subscribed email. This version is for the
# raw lambda function and so has the session key passed in as a string
def validate_request_lambda(request_json, headers, function_name, correlation_id, raiseOnError=True):
    session = request_json.get('session')
    organization = request_json.get('organization')
    version = request_json.get('version')

    # Check for x-signed-identity header (or any casing variation)
    signed_identity = next((value for key, value in headers.items() if key.lower() == 'x-signed-identity'), None) if headers is not None else None
    if signed_identity:
        try:
            signing_key = get_jwt_signing_key()  # Function to retrieve the public key

            # look for signing algorithm out of headers using same case invariant approach, defaulting to RS256
            signing_algorithm = next((value for key, value in headers.items() if key.lower() == 'x-signing-algorithm'), 'RS256')

            # Decode and verify JWT
            identity = jwt.decode(signed_identity, signing_key, algorithms=[signing_algorithm])

            # Validate expiration time
            if identity.get('expires') and identity['expires'] < datetime.now().timestamp():
                raise jwt.ExpiredSignatureError("Signed identity expired")

            if 'email' not in identity:
                raise jwt.InvalidTokenError("Invalid signed identity- missing email")
            email = identity['email']

            if 'organization' in identity:
                organization = identity['organization']
            elif organization is None:
                raise jwt.InvalidTokenError("Invalid signed identity- missing organization")

        except jwt.ExpiredSignatureError as e:
            if raiseOnError:
                raise ExtendedUnauthorizedError(str(e))
            else:
                print(f'Error: {e}')
                return {'enabled': False, 'status': 'unauthorized'}

        except Exception as e:
            if raiseOnError:
                raise ExtendedUnauthorizedError("Invalid signed identity")
            else:
                print(f'Error: Invalid signed identity: {e}')
                return {'enabled': False, 'status': 'unauthorized'}

    else:
        # if session is missing, the client isn't authorized
        if session is None:
            raise ExtendedUnauthorizedError("Invalid authentication/authorization", reason="InvalidSession")

        if version is None:
            if raiseOnError:
                raise ExtendedUnauthorizedError("Please upgrade your client software to use Boost service", reason="UpgradeRequired")
            else:
                print('Error: Please upgrade your client software to use Boost service')
                return {'enabled': False, 'status': 'unregistered'}

        elif organization is None:
            if raiseOnError:
                raise ExtendedUnauthorizedError("Missing account organization from client request", reason="MissingOrganization")
            else:
                print('Error: Missing account organization from client request')
                return {'enabled': False, 'status': 'unregistered'}

        # otherwise check to see if we have a valid github session token
        # parse the request body as json
        try:
            # extract the code from the json data
            validated, email = validate_github_session(session, organization, correlation_id, raiseOnError)
        except ValueError:
            pass

        # if we did not get a valid email, send a cloudwatch alert and raise the error
        if not validated:
            capture_metric({"name": organization, "id": "UNKNOWN"}, email, function_name, correlation_id,
                           {"name": InfoMetrics.GITHUB_ACCESS_NOT_FOUND, "value": 1, "unit": "None"})

            if raiseOnError:
                # if we got here, we failed, return an error
                raise ExtendedUnauthorizedError("Error: Please login to GitHub and select an Organization to use this service", reason="GitHubAccessNotFound")
            else:
                print(f'Error:{email}: Please login to GitHub and select an Organization to use this service')
                return {'enabled': False, 'status': 'unregistered'}

    signed_user = signed_identity is not None

    # if we got this far, we got a valid email. now check that the email is subscribed
    account = check_valid_subscriber(signed_user, email, organization, correlation_id, not raiseOnError)

    # if not validated, we need to see if we have a billing error, or if the user is not subscribed
    if not account['enabled']:
        if account and account['status'] == 'suspended':
            if raiseOnError:
                raise ExtendedAccountBillingError("Billing error: Please check your credit card on file and that you have an active Polyverse Boost subscription")
            else:
                print(f'Billing error:{email}: Please check your credit card on file and that you have an active Polyverse Boost subscription')
        elif account and account['status'] == 'expired':
            if raiseOnError:
                raise ExtendedAccountBillingError("Boost Trial Expired: Your Boost trial license has expired. To continue using Boost service, please visit your account dashboard and update your payment information.")
            else:
                print(f'Boost Trial Expired:{email}: Your Boost trial license has expired. To continue using Boost service, please visit your account dashboard and update your payment information.')
        else:
            account = {'status': 'unregistered'}
            if raiseOnError:
                raise ExtendedUnauthorizedError("Error: Please subscribe to use Polyverse Boost service", reason="InvalidSubscriber")
            else:
                print(f'Error:{email}: Please subscribe to Polyverse Boost service')

    return account


def clean_account(account, email=None, organization=None):
    # if we are in an extreme error path without account info
    #   then return unknown for status and email
    if (account is None):
        return {
            'enabled': False,
            'status': 'unknown',
            'org': organization if organization is not None else 'unknown',
            'email': email if email is not None else 'unknown',
        }

    return {
        'enabled': account['enabled'],
        'status': account['status'],
        'operation_cost': account['operation_cost'] if 'operation_cost' in account else 0.00,
        'operation_expense': account['operation_expense'] if 'operation_expense' in account else 0.00,
        'org': account['org'] if 'org' in account else organization if organization is not None else 'unknown',
        'email': account['email'] if 'email' in account else email if email is not None else 'unknown',
    }


# "user-agent": "Boost-VSCE/0.9.7"
def extract_client_version(event_params):
    if ('headers' not in event_params):
        return None

    headers = event_params['headers']

    if ('User-Agent' not in headers and 'user-agent' not in headers):
        return None
    user_agent = headers.get('User-Agent', headers.get('user-agent', ''))

    # Example: assuming the client version is appended to the user agent string
    parts = user_agent.split('/')
    if len(parts) > 1:
        return parts[1]

    return None


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
