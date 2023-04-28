import stripe
import math
import uuid
import time

from . import pvsecret

secret_json = pvsecret.get_secrets()

stripe.api_key = secret_json["stripe"]
print("stripe key ", secret_json["stripe"])

# a function to call stripe to create a customer
def check_create_customer(email, org):
    #the Stripe API is a bit goofy.  search does not guarantee results immediately, it can have up to an hour delay.
    #so we will first search.
    #if we can't find it, then we look to the last hour of customers and see if we can find it there.
    #if we still can't find it, then we create it.

    #first see if the customer already exists, we need to look at the org field in metadata
    customers = stripe.Customer.search(query="metadata['org']:'{}'".format(org), expand=['data.subscriptions'])
    for customer in customers.data:
        if customer.metadata.org == org:
            return customer

    # Calculate the timestamp for one hour ago
    one_hour_ago = int(time.time()) - 3600

    # Search for customers created in the last hour if search fails
    customers = stripe.Customer.list(created={'gte': one_hour_ago}, expand=['data.subscriptions'])

    for customer in customers.data:
        if customer.metadata.org == org:
            return customer
        
    customer = stripe.Customer.create(
        name=org,
        email=email,
        metadata={"org": org},
    )

    return customer

def check_create_subscription(customer, email):
    print("customer id is ", customer.id, email)
    #first see if the customer already has a subscription. this can be found on the subscription field of the customer. make sure the field exists first!

    #check if the subscriptions field exists
    if hasattr(customer, 'subscriptions'):
        subscriptions = customer.subscriptions
        for subscription in subscriptions.data:
            print("subscription status for id ", subscription.id, " is ", subscription.status)
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
    print("subscription id ", subscription.id)
    subscription_items = stripe.SubscriptionItem.list(subscription=subscription.id)
    for subscription_item in subscription_items.data:
        #if the email in the metadata matches the email we are looking for, return the subscription item
        print("checking subscription item metadata ", subscription_item.metadata.email, email)
        if subscription_item.metadata.email == email:
            return subscription_item
    
    #if not, create a subscription
    print("trying to create subscription item")
    print(subscription.id)
    print(email)

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
    
def check_valid_subscriber(email, organization):
    customer = check_create_customer(email=email, org=organization)
    if not customer:
        return False
    subscription = check_create_subscription(customer=customer, email=email)
    if not subscription:
        return False
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)
    if not subscription_item:
        return False
    
    expired = check_trial_expired(customer=customer)
    if not expired:
        return True
    else:
        return False
