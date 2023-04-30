import requests
import shopify
from . import pvsecret
from chalice import UnauthorizedError
import re
from chalicelib.telemetry import cw_client, xray_recorder
import time
from .payments import check_valid_subscriber

class ExtendedUnauthorizedError(UnauthorizedError):
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason

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

def fetch_orgs(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }
    url = 'https://api.github.com/user/orgs'

    response = requests.get(url, headers=headers)
    orgs = response.json()
    #we just need the string of the org name, it's in the 'login' field.  update the orgs array to just be the string
    if isinstance(orgs, list):
        for i in range(len(orgs)):
            orgs[i] = orgs[i]['login']
            
    return orgs

# function to get the domain from an email address, returns true if validated, and returns email if found in token
def validate_github_session(access_token, organization, correlation_id):
    if cw_client is not None:
        with xray_recorder.capture('github_verify_email'):
            email = fetch_email(access_token)
            orgs = fetch_orgs(access_token)
    else:
        start_time = time.monotonic()
        email = fetch_email(access_token)
        orgs = fetch_orgs(access_token)
        end_time = time.monotonic()
        print(f'Execution time {correlation_id} github_verify_email: {end_time - start_time:.3f} seconds')

    print('BOOST_USAGE: email is ', email)

    #make sure that organization is in the list of orgs, make sure orgs is an array then loop through
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
def validate_request_lambda(request_json, correlation_id):

    session = request_json.get('session')
    organization = request_json.get('organization')
    version = request_json.get('version')

    #if no version or organization specified, then we need to ask the client to upgrade
    if version is None or organization is None:
        raise ExtendedUnauthorizedError("Error: please upgrade to use this service", reason="UpgradeRequired")

    # otherwise check to see if we have a valid github session token
    # parse the request body as json
    try:
        # extract the code from the json data
        validated, email = validate_github_session(session, correlation_id)

    except ValueError:
        pass

    # if we did not get a valid email, send a cloudwatch alert and raise the error
    if not validated:
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
        raise ExtendedUnauthorizedError("Error: please login to github to use this service", reason="GitHubAccessNotFound")
    
    #if we got this far, we got a valid email. now check that the email is subscribed

    print('callling check_valid_subscriber', email, organization)
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
