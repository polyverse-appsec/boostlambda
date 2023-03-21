import requests
import shopify
from . import pvsecret

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
        print(f'Error: {response.status_code}')
        return None

def validate_github_session(access_token):
    email = fetch_email(access_token)
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
    #alex = shopify.Customer.search(query=f'email:{email}')
    customers = shopify.Customer.find(email=email)

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


