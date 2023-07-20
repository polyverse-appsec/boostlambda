import stripe
import math
import uuid
import time
import os
from chalicelib.version import API_VERSION
from chalice import UnauthorizedError
from . import pvsecret
from chalicelib.telemetry import capture_metric, InfoMetrics
import traceback
import random

customerportal_api_version = API_VERSION  # API version is global for now, not service specific
print("customerportal_api_version: ", customerportal_api_version)

if 'AWS_CHALICE_CLI_MODE' not in os.environ:
    secret_json = pvsecret.get_secrets()

    service_stage = variable_value = os.getenv('CHALICE_STAGE')
    if (service_stage == "prod" or service_stage == "staging"):
        stripe.api_key = secret_json["stripe_prod"]
    else:  # dev, test, or local
        stripe.api_key = secret_json["stripe_dev"]


class ExtendedAccountBillingError(UnauthorizedError):
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason


def stripe_retry(func, *args, **kwargs):
    retry_count = 0
    max_retries = 1

    while retry_count <= max_retries:
        try:
            # Call the Stripe function
            response = func(*args, **kwargs)

            if retry_count > 0:
                print(f"Successful Stripe call to {func.__name__}: after attempt {retry_count + 1} retry of {max_retries + 1}")

            return response
        except stripe.error.APIConnectionError as e:
            if retry_count < max_retries:
                wait_time = random.randint(3, 5)  # Random wait between 3 to 5 seconds
                time.sleep(wait_time)
                print(f"Connection error occurred with Stripe call {func.__name__}: {str(e)}; attempt {retry_count + 1} of {max_retries + 1} after {wait_time} seconds")
                retry_count += 1
            else:
                print(f"Connection error: {str(e)} Max retries exceeded: {max_retries} retrieving Stripe call: {func.__name__}... giving up")
                raise e


def create_price(email):
    # price_id = "boost_per_kb"  # original Boost pricing on input only
    price_id = "boost_per_kb_launch"  # new Boost pricing on combined input+output only

    # Retrieve the existing Price object
    original_price = stripe_retry(stripe.Price.retrieve, price_id, expand=['tiers'])

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
    new_price = stripe_retry(stripe.Price.create,
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
def check_create_customer(email, org, correlation_id=0):
    # the Stripe API is a bit goofy.  search does not guarantee results immediately, it can have up to an hour delay.
    # so we will first search.
    # if we can't find it, then we look to the last hour of customers and see if we can find it there.
    # if we still can't find it, then we create it.

    # first see if the customer already exists, we need to look at the org field in metadata
    customers = stripe_retry(stripe.Customer.search, query="metadata['org']:'{}'".format(org), expand=['data.subscriptions'])
    for customer in customers.data:
        if customer.metadata.org == org:
            return customer

    # Calculate the timestamp for one hour ago
    one_hour_ago = int(time.time()) - 3600

    # Search for customers created in the last hour if search fails
    customers = stripe_retry(stripe.Customer.list, created={'gte': one_hour_ago}, expand=['data.subscriptions'])

    for customer in customers.data:
        if customer.metadata.org == org:
            return customer

    try:
        customer = stripe_retry(stripe.Customer.create,
                                name=org,
                                email=email,
                                metadata={"org": org},
                                )
        print(f"CREATE_CUSTOMER:SUCCEEDED:: email:{email}, org:{org}")
        capture_metric(customer, email, correlation_id, "create_customer",
                       {"name": InfoMetrics.NEW_CUSTOMER, "value": 1, "unit": "None"})

    except Exception:
        exception_info = traceback.format_exc().replace('\n', ' ')
        print(f"CREATE_CUSTOMER:FAILED:: email:{email}, org:{org}, Error:{exception_info}")
        capture_metric({"name": org, "id": exception_info}, email, correlation_id, "create_customer",
                       {"name": InfoMetrics.NEW_CUSTOMER_ERROR, "value": 1, "unit": "None"})
        raise

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
    subscription = stripe_retry(stripe.Subscription.create,
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
    subscription_items = stripe_retry(stripe.SubscriptionItem.list, subscription=subscription.id)
    for subscription_item in subscription_items.data:
        # if the email in the metadata matches the email we are looking for, return the subscription item
        if subscription_item.metadata.email == email:
            return subscription_item

    # if not, create a subscription

    # we need to create a price per email address
    price = create_price(email)

    subscription_item = stripe_retry(stripe.SubscriptionItem.create,
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
    stripe_retry(stripe.SubscriptionItem.create_usage_record,
                 id=subscription_item.id,
                 quantity=usage,
                 idempotency_key=idempotency_key
                 )
    return subscription_item


def update_usage_for_text(account, bytes_of_text):
    # get the subscription item
    subscription_item = account['subscription_item']
    # update the usage
    update_usage(subscription_item, bytes_of_text)


# Check if the customer has a non-zero balance and if they do NOT have a payment method
# in this case, we know their trial has expired.
# there are two ways to check balance, balance and a pending invoice. it's not clear which is the better way yet
# so we will check both
# account_status result:
#   - suspended: the customer does not have a payment method, and has pending invoice > 0
#   - trial: the customer does not have a payment method, and has pending invoice = 0
#   - paid: the customer has a payment method
#   - active: the customer has no usage, no invoice, no balance, no payment method
def check_customer_account_status(customer):

    # if stripe thinks the customer is delinquent, then we will suspend them
    if customer['delinquent'] is True:
        return False, "suspended"

    invoice = stripe_retry(stripe.Invoice.upcoming, customer=customer.id)

    # We're going to treat polyverse accounts as paid, even if no credit card on file
    if customer['email'].endswith(("@polyverse.io", "@polytest.ai", "@polyverse.com")):
        return True, "paid"

    # Check if the customer has a default payment method (or manually entered payment)
    if customer['invoice_settings']['default_payment_method'] or customer['default_source']:
        return True, "paid"

    # it seems like a non-zero balance also implies a trial license
    # we return false to notify that trial has expired (e.g. all discounts used up, and amount due)
    open_due = customer['balance'] + invoice.amount_due
    if open_due > 0:
        open_credit = customer['discount']['coupon']['amount_off'] if \
            customer['discount'] and customer['discount']['coupon'] and \
            customer['discount']['coupon']['amount_off'] else 0
        if open_due >= open_credit:
            return False, "expired"

    # if there is active trial usage, then we will assume they are still in trial
    if invoice.total_discount_amounts and invoice.total_discount_amounts[0].amount > 0:
        return True, "trial"

    # no usage, no invoice, no balance, no payment method, so we'll assume new customer
    return True, "active"


# if we fail validation, caller can stop call. if we pass validation, caller can continue
def check_valid_subscriber(email, organization, correlation_id):

    if (email is None):
        raise Exception("Email is required to create a subscription account")

    customer = check_create_customer(email=email, org=organization, correlation_id=correlation_id)
    if not customer:
        return False, None
    subscription = check_create_subscription(customer=customer, email=email)
    if not subscription:
        return False, None
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)
    if not subscription_item:
        return False, None

    # return a dict with the customer, subscription, and subscription_item
    active, account_status = check_customer_account_status(customer=customer)
    account = {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
    account['status'] = account_status

    return active, account


def customer_portal_url(account):
    session = stripe_retry(stripe.billing_portal.Session.create,
                           customer=account['customer'].id,
                           return_url='https://polyverse.com',
                           )
    return session
