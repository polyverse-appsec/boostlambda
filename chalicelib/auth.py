import requests
from chalice import UnauthorizedError
import re
from chalicelib.telemetry import cloudwatch, xray_recorder, capture_metric, InfoMetrics
import time
from .payments import check_valid_subscriber


class ExtendedUnauthorizedError(UnauthorizedError):
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason


def fetch_email_and_username(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }
    url = 'https://api.github.com/user'

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user = response.json()
        return user['email'], user['login']
    else:
        email_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(email_pattern, access_token)

        if match:
            return match.group(1), match.group(1)
        return None, None


def fetch_orgs(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }
    url = 'https://api.github.com/user/orgs'

    response = requests.get(url, headers=headers)
    # if we got a 200, then we have a list of orgs, otherwise check for a testorg
    if response.status_code == 200:
        orgs = response.json()
        # we just need the string of the org name, it's in the 'login' field.  update the orgs array to just be the string
        if isinstance(orgs, list):
            for i in range(len(orgs)):
                orgs[i] = orgs[i]['login']

        return orgs
    else:
        org_pattern = r'testemail:\s*([\w.-]+@[\w.-]+\.\w+)'
        match = re.search(org_pattern, access_token)

        if match:
            email = match.group(1)
            org = get_domain(email)
            return [org]
        return None


# function to get the domain from an email address, returns true if validated, and returns email if found in token
def validate_github_session(access_token, organization, correlation_id, context):
    if cloudwatch is not None:
        with xray_recorder.capture('github_verify_email'):
            email, username = fetch_email_and_username(access_token)
            orgs = fetch_orgs(access_token)
    else:
        start_time = time.monotonic()
        email, username = fetch_email_and_username(access_token)
        orgs = fetch_orgs(access_token)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} github_verify_email: {end_time - start_time:.3f} seconds')

    print('BOOST_USAGE: email is ', email)

    # make sure that organization is in the list of orgs, make sure orgs is an array then loop through
    if orgs is not None:
        if isinstance(orgs, list):
            for org in orgs:
                if org == organization:
                    return True, email
        else:
            if orgs == organization:
                return True, email
    return False, email


# function to validate that the request came from a github logged in user or we are running on localhost
# or that the session token is valid github oauth token for a subscribed email. This version is for the
# raw lambda function and so has the session key passed in as a string
def validate_request_lambda(request_json, context, correlation_id):

    session = request_json.get('session')
    organization = request_json.get('organization')
    version = request_json.get('version')

    # if no version or organization specified, then we need to ask the client to upgrade
    if version is None or organization is None:
        raise ExtendedUnauthorizedError("Error: please upgrade to use this service", reason="UpgradeRequired")

    # otherwise check to see if we have a valid github session token
    # parse the request body as json
    try:
        # extract the code from the json data
        validated, email = validate_github_session(session, organization, correlation_id, context)
    except ValueError:
        pass

    # if we did not get a valid email, send a cloudwatch alert and raise the error
    if not validated:
        capture_metric(email, correlation_id, context,
                       {"name": InfoMetrics.GITHUB_ACCESS_NOT_FOUND, "value": 1, "unit": "None"})

        # if we got here, we failed, return an error
        raise ExtendedUnauthorizedError("Error: please login to github to use this service", reason="GitHubAccessNotFound")

    # if we got this far, we got a valid email. now check that the email is subscribed

    valid, account = check_valid_subscriber(email, organization)

    if not valid:
        raise ExtendedUnauthorizedError("Error: please subscribe to use this service", reason="InvalidSubscriber")

    return True, account


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
