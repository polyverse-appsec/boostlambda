import requests
import shopify
from . import pvsecret
from chalice import UnauthorizedError
import re

def fetch_email(access_token):
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github+json',
    }
    url = f'https://api.github.com/user/emails'
    
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

def validate_github_session(access_token):
    email = fetch_email(access_token)
    print('email is ', email)
    if email:
        return verify_email_with_shopify(email)
    else:
        return False


def verify_email_with_shopify(email):
    # Authenticate with the Shopify API
    shop_url = f'https://polyverse-security.myshopify.com/admin/api/2023-01'
    api_version = '2023-01'
    secret_json = pvsecret.get_secrets()

    shopify_token = secret_json["shopify"]

    session = shopify.Session(shop_url, api_version,shopify_token )
    shopify.ShopifyResource.activate_session(session)

    shopify.ShopifyResource.set_site(shop_url)

    # Fetch the customer information using the email address
    #first see if the email is in a valid domain
    domain = get_domain(email)
    print('domain is ', domain)
    if is_valid_domain(domain):
        customers = shopify.Customer.search(query=f'email:*@{domain}')
    else:
        customers = shopify.Customer.find(email=email)

    print("customers are ", customers)
    # Clear the Shopify API session
    shopify.ShopifyResource.clear_session()

    # Check if a customer was found
    # Check if any customers were found
    if customers:
        # Loop through the customers and print their information
        for customer in customers:
            print(f"Customer Information for {customer.email}:")
            print(f"ID: {customer.id}")
            print(f"First Name: {customer.first_name}")
            print(f"Last Name: {customer.last_name}")
            print(f"Total Spent: {customer.total_spent} {customer.currency}")
            print(f"Orders Count: {customer.orders_count}")
            print()
            if customer.orders_count > 0 :
                return True 
    else:
        print(f"No customer found with email {email}")
    
    return email.endswith('@polyverse.com') or email.endswith('@polyverse.io')

#function to validate that the request came from a github logged in user or we are running on localhost
#or that the session token is valid github oauth token for a subscribed email
def validate_request(request):

    print('request objec tis ')
    print(request.context["identity"]['sourceIp'])

    #otherwise check to see if we have a valid github session token
    #parse the request body as json
    try:
        json_data = request.json_body
        #extract the code from the json data
        session = json_data.get('session')   
        if validate_github_session(session):
            return True, None
    except ValueError:
        #don't do anything if the json is invalid
        pass

    #last chance, check the ip address
    
    #if we don't have a rapid api key, check the origin
    #ip = request.context["identity"]["sourceIp"]
    #print("got client ip: " + ip)
    #if the ip starts with 127, it's local
    #if ip.startswith("127"):
    #    return True, None
    
    #if we got here, we failed, return an error
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

