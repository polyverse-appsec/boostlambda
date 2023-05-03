import stripe
import math
import uuid
import time
import os

from . import pvsecret

secret_json = pvsecret.get_secrets()

service_stage = variable_value = os.getenv('CHALICE_STAGE')
if (service_stage == "prod" or service_stage == "staging"):
    stripe.api_key = secret_json["stripe_prod"]
else:  # dev, test, or local
    stripe.api_key = secret_json["stripe_dev"]


def create_price(email):
    # price_id = "boost_per_kb"  # original Boost pricing on input only
    price_id = "boost_per_kb_launch"  # new Boost pricing on combined input+output only

    # Retrieve the existing Price object
    original_price = stripe.Price.retrieve(price_id, expand=['tiers'])

    # Extract relevant attributes from the original Price object
    currency = original_price['currency']
    product = original_price['product']
    billing_scheme = original_price['billing_scheme']
    tiers = original_price['tiers']
    tiers_mode = original_price['tiers_mode']

    # add the email to the nickname
    # Use the 'get' method to retrieve the value of 'nickname' from the dictionary, with a default value of an empty string
    nickname_value = original_price.get('nickname', '')

    # Use a conditional expression to check if the value of 'nickname' is None before performing the concatenation
    if (nickname_value is not None):
        nickname = nickname_value + '_' + email
    else:
        nickname = 'price_' + email
    recurring = original_price['recurring']

    # stripe will give us both flat_amount and _flat_amount_decimal, as well as unit_amount_decimal in the tiers array
    # we need to use the regular flat_amount one. detele the decimal ones
    for tier in tiers:
        if 'flat_amount_decimal' in tier:
            del tier['flat_amount_decimal']
        if 'unit_amount_decimal' in tier:
            del tier['unit_amount_decimal']

    # now set the up_to attribute to the max value
    tiers[1]['up_to'] = 'inf'

    # Create a new Price object with the same attributes as the original one
    new_price = stripe.Price.create(
        currency=currency,
        product=product,
        billing_scheme=billing_scheme,
        tiers=tiers,
        tiers_mode=tiers_mode,
        nickname=nickname,
        recurring=recurring,
        metadata={
            "email": email
        }
    )

    return new_price


# a function to call stripe to create a customer
def check_create_customer(email, org):
    # the Stripe API is a bit goofy.  search does not guarantee results immediately, it can have up to an hour delay.
    # so we will first search.
    # if we can't find it, then we look to the last hour of customers and see if we can find it there.
    # if we still can't find it, then we create it.

    # first see if the customer already exists, we need to look at the org field in metadata
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
    # first see if the customer already has a subscription. this can be found on the subscription field of the customer. make sure the field exists first!

    # check if the subscriptions field exists
    if hasattr(customer, 'subscriptions'):
        subscriptions = customer.subscriptions
        for subscription in subscriptions.data:
            if subscription.status == "active":
                return subscription

    if (email is None):
        raise Exception("Email is required to create a payment account")

    # if we got here, we don't have a subscription, so create one
    # we need to create a price per email address
    price = create_price(email)
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[
            {
                "price": price.id,
                "metadata": {"email": email}
            },
        ],
        billing_thresholds={
            'amount_gte': 100000,
            'reset_billing_cycle_anchor': False,
        },
        coupon="RNhiqVPC"
    )
    return subscription


# find or create a subscription item which uses email in the metadata, and using the boost_per_kb price
def check_create_subscription_item(subscription, email):
    # first see if the customer already has a subscription
    subscription_items = stripe.SubscriptionItem.list(subscription=subscription.id)
    for subscription_item in subscription_items.data:
        # if the email in the metadata matches the email we are looking for, return the subscription item
        if subscription_item.metadata.email == email:
            return subscription_item

    # if not, create a subscription

    # we need to create a price per email address
    price = create_price(email)

    subscription_item = stripe.SubscriptionItem.create(
        subscription=subscription.id,
        price=price.id,
        metadata={"email": email}
    )

    return subscription_item


def update_usage(subscription_item, bytes):
    # calculate the usage by dividing the bytes by 1024 and rounding up

    usage = math.ceil(bytes / 1024)
    idempotency_key = str(uuid.uuid4())

    # update the usage
    stripe.SubscriptionItem.create_usage_record(
        id=subscription_item.id,
        quantity=usage,
        idempotency_key=idempotency_key
    )
    return subscription_item


def update_usage_for_code(account, code):
    # get the subscription item
    subscription_item = account['subscription_item']
    # get the bytes from the code (the length of the code)
    bytes = len(code)
    # update the usage
    update_usage(subscription_item, bytes)


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

    if (email is None):
        raise Exception("Email is required to create a subscription account")

    customer = check_create_customer(email=email, org=organization)
    if not customer:
        return False, None
    subscription = check_create_subscription(customer=customer, email=email)
    if not subscription:
        return False, None
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)
    if not subscription_item:
        return False, None

    # return a dict with the customer, subscription, and subscription_item
    expired = check_trial_expired(customer=customer)
    if not expired:
        return True, {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
    else:
        return False, None


def customer_portal_url(account):
    session = stripe.billing_portal.Session.create(
        customer=account['customer'].id,
        return_url='https://polyverse.com',
    )
    return session
