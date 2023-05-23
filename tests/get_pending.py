import os
import json
import boto3
from botocore.exceptions import ClientError
import stripe

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
        raise e

    awssecret = get_secret_value_response['SecretString']
    secret_json = json.loads(awssecret)
    secret_json['stripe'] = secret_json['stripe_prod']
    
    return secret_json

def main():
    secrets = get_secrets()
    stripe.api_key = secrets['stripe']

    total_pending_invoices = 0
    customers = stripe.Customer.list()
    
    for customer in customers.auto_paging_iter():
        try:
            #if there is no metadata field or the field org does not exist, skip this customer
            if 'metadata' not in customer or 'org' not in customer.metadata:    
                continue     
            invoice = stripe.Invoice.upcoming(customer=customer.id)
            print(f"Customer: {customer.email} / {customer.metadata.org}, Pending Invoice Amount: {invoice.amount_due}")
            total_pending_invoices += invoice.amount_due
        except Exception as e:
            print(customer)
            print(f"No upcoming invoice for customer {customer.id} or error fetching invoice: {str(e)}")

    print(f"\nTotal Pending Invoice Amount for all Customers: {total_pending_invoices}")

if __name__ == "__main__":
    main()

