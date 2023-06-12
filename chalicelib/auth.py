import requests
from chalice import UnauthorizedError
import re
from chalicelib.telemetry import cloudwatch, xray_recorder, capture_metric, InfoMetrics
import time
from .payments import check_valid_subscriber, ExtendedAccountBillingError
from chalicelib.version import API_VERSION
from cachetools import TTLCache

userorganizations_api_version = API_VERSION  # API version is global for now, not service specific
print("userorganizations_api_version: ", userorganizations_api_version)


class ExtendedUnauthorizedError(UnauthorizedError):
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason


# Create a cache with a time-to-live (TTL) of 5 minutes
token_2_email_cache = TTLCache(maxsize=100, ttl=300)


def fetch_email(access_token):
    # Check if the access token is already cached
    if access_token in token_2_email_cache:
        return token_2_email_cache[access_token]
    else:
        print("Refreshing Org Cache: *access token hidden*")

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
                # Cache the access token and its corresponding email
                print(f"Cached GitHub Auth Token: {email['email']}")
                token_2_email_cache[access_token] = email['email']
                return email['email']
    else:
        email_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(email_pattern, access_token)

        if match:
            email = match.group(1)
            # Cache the access token and its corresponding email
            print(f"Cached GitHub Auth Token: {email}")
            token_2_email_cache[access_token] = email
            return email

        print(f"ERROR: GitHub email query failure: {response.json()}")

        return None


# Create a cache with a time-to-live (TTL) of 5 minutes
token_2_user_cache = TTLCache(maxsize=100, ttl=300)


def fetch_email_and_username(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }

    # get email from github
    email = fetch_email(access_token)
    if email is None:
        raise Exception("GitHub Email is required to access Boost account")

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
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user = response.json()
        username = user['login']

        # Cache the username for future use
        token_2_user_cache[access_token] = username

        return email, username
    else:
        email_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(email_pattern, access_token)

        if match:
            username = match.group(1)

            # Cache the username for future use
            token_2_user_cache[access_token] = username

            return username, username

        print(f"ERROR: GitHub User query failure: {response.json()}")

        return None, None


# Create a cache with a time-to-live (TTL) of 5 minutes
token_2_org_cache = TTLCache(maxsize=100, ttl=300)


def fetch_orgs(access_token):
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
    response = requests.get(url, headers=headers)
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
            org = get_domain(email)
            orgs = [org]

            # Cache the orgs for future use
            token_2_org_cache[access_token] = orgs

            return orgs

        print(f"ERROR: GitHub Org query failure: {response.json()}")

        return None


# function to get the domain from an email address, returns true if validated, and returns email if found in token
def validate_github_session(access_token, organization, function_name, correlation_id):
    if cloudwatch is not None:
        with xray_recorder.capture('fetch_email_and_username'):
            email, username = fetch_email_and_username(access_token)
    else:
        start_time = time.monotonic()
        email, username = fetch_email_and_username(access_token)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} fetch_email_and_username: {end_time - start_time:.3f} seconds')

    # if the username matches the user's requested org, then we'll use a "personal" org
    if username == organization:
        return True, email

    # otherwise, we validate the user's requested organization against their GitHub org list
    if cloudwatch is not None:
        with xray_recorder.capture('fetch_orgs'):
            orgs = fetch_orgs(access_token)
    else:
        start_time = time.monotonic()
        orgs = fetch_orgs(access_token)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} fetch_orgs: {end_time - start_time:.3f} seconds')

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
def validate_request_lambda(request_json, function_name, correlation_id, raiseOnError=True):

    session = request_json.get('session')
    organization = request_json.get('organization')
    version = request_json.get('version')

    # if no version or organization specified, then we need to ask the client to upgrade
    if version is None:
        if raiseOnError:
            raise ExtendedUnauthorizedError("Please upgrade your client software to use Boost service", reason="UpgradeRequired")
        else:
            print('Error: Please upgrade your client software to use Boost service')
            return False, {'status': 'unregistered'}

    elif organization is None:
        if raiseOnError:
            raise ExtendedUnauthorizedError("Missing account organization from client request", reason="MissingOrganization")
        else:
            print('Error: Missing account organization from client request')
            return False, {'status': 'unregistered'}

    # otherwise check to see if we have a valid github session token
    # parse the request body as json
    try:
        # extract the code from the json data
        validated, email = validate_github_session(session, organization, function_name, correlation_id)
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
            return False, {'status': 'unregistered'}

    # if we got this far, we got a valid email. now check that the email is subscribed
    validated, account = check_valid_subscriber(email, organization, correlation_id)

    # if not validated, we need to see if we have a billing error, or if the user is not subscribed
    if not validated:
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

    return validated, account


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
