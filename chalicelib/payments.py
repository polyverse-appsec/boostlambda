import stripe
import math
import uuid

from . import pvsecret

secret_json = pvsecret.get_secrets()

stripe.api_key = secret_json["stripe"]
print("stripe key ", secret_json["stripe"])

# a function to call stripe to create a customer
def check_create_customer(email, org):
    #first see if the customer already exists, we need to look at the org field in metadata
    customers = stripe.Customer.search(query='metadata["org"]: "{}"'.format(org), expand=['data.subscriptions'])
                                     
    for customer in customers.data:
        if customer.metadata.org == org:
            return customer

    customer = stripe.Customer.create(
        email=email,
        metadata={"org": org},
    )
    return customer

def check_create_subscription(customer, email):
    #first see if the customer already has a subscription. this can be found on the subscription field of the customer. make sure the field exists first!

    #check if the subscriptions field exists
    if hasattr(customer, 'subscriptions'):
        subscriptions = customer.subscriptions
        for subscription in subscriptions.data:
            if subscription.status == "active":
                return subscription

     #if we got here, we don't have a subscription, so create one

    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[
            {
                "price": "boost_per_kb",
                "metadata": {"email": email}
            },
        ],
        coupon="RNhiqVPC"
    )
    return subscription

# find or create a subscription item which uses email in the metadata, and using the boost_per_kb price

def check_create_subscription_item(subscription, email):
    #first see if the customer already has a subscription
    subscription_items = stripe.SubscriptionItem.list(subscription=subscription.id)
    for subscription_item in subscription_items.data:
        #if the email in the metadata matches the email we are looking for, return the subscription item
        if subscription_item.metadata.email == email:
            return subscription_item
    
    #if not, create a subscription
    subscription_item = stripe.SubscriptionItem.create(
        subscription=subscription.id,
        price="boost_per_kb",
        metadata={"email": email},
    )

    return subscription_item

def update_usage(subscription_item, bytes):
    #calculate the usage by dividing the bytes by 1024 and rounding up

    usage = math.ceil(bytes / 1024)
    idempotency_key = str(uuid.uuid4())

    #update the usage
    stripe.SubscriptionItem.create_usage_record(
        id=subscription_item.id,
        quantity=usage,
        idempotency_key=idempotency_key
    )
    return subscription_item

def check_trial_expired(customer):
    # Check if the customer has a non-zero balance and if they do NOT have a payment method
    # in this case, we know their trial has expired.
    # there are two ways to check balance, balance and a pending invoice. it's not clear which is the better way yet
    # so we will check both
    invoice = stripe.Invoice.upcoming(customer=customer.id)
    if customer['balance'] > 0 or invoice.amount_due > 0:
        # Check if the customer has a default payment method
        if not customer['invoice_settings']['default_payment_method']:
            return True
    
    # If we got here, the trial has not expired or they have a payment method
    return False
    
