# test_payments.py
import stripe
from chalice.test import Client
import json
from app import app

from . import test_utils  # noqa pylint: disable=unused-import

# Import the checkCreateCustomer function from the payments module in the chalicelib directory
from chalicelib.payments import check_create_customer, check_create_subscription, check_create_subscription_item, update_usage, check_customer_account_status, check_valid_subscriber
from chalicelib.usage import boost_cost_per_kb, boost_base_monthly_cost


# utility function to generate an org name with a random domain
def generate_org():
    import random
    import string
    # Generate a random string of 10 lowercase letters for the domain
    org = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
    org = 'test-org-' + org
    return org


def generate_email(domain):
    import random
    import string
    # Generate a random string of 10 lowercase letters for the domain
    email = ''.join(random.choice(string.ascii_lowercase) for i in range(10)) + domain
    email = 'test-email-' + email
    return email


# Define a test function using the pytest naming convention (test_*)
def test_check_create_customer():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # Call the checkCreateCustomer function with the test inputs
    result = check_create_customer(email=email, org=org, correlation_id="test")

    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None

    # now create a second customer with the same email and make sure we get the same customer back
    result2 = check_create_customer(email=email, org=org, correlation_id="test")
    assert result2 is not None
    assert result2.id is not None
    assert result2.id == result.id

    # now create a third customer with a different email and the same org and make sure we get the same customer back
    email2 = generate_email("@" + org + ".com")
    result3 = check_create_customer(email=email2, org=org, correlation_id="test")
    assert result3 is not None
    assert result3.id is not None
    assert result3.id == result.id

    # now create a fourth customer with a different email and a different org and make sure we get a different customer back
    org2 = generate_org()
    email3 = generate_email("@" + org2 + ".com")
    result4 = check_create_customer(email=email3, org=org2, correlation_id="test")
    assert result4 is not None
    assert result4.id is not None
    assert result4.id != result.id


def test_check_create_subscription():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # Call the checkCreateCustomer function with the test inputs
    customer = check_create_customer(email=email, org=org)

    # Call the checkCreateSubscription function with the test inputs
    result = check_create_subscription(customer=customer, email=email)

    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None


def test_check_create_subscription_item():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # Call the checkCreateCustomer function with the test inputs
    customer = check_create_customer(email=email, org=org)

    # Call the checkCreateSubscription function with the test inputs
    subscription = check_create_subscription(customer=customer, email=email)

    # Call the checkCreateSubscriptionItem function with the test inputs
    result = check_create_subscription_item(subscription=subscription, email=email)

    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None


def test_update_usage_base():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # Call the checkCreateCustomer function with the test inputs
    customer = check_create_customer(email=email, org=org)

    # Call the checkCreateSubscription function with the test inputs
    subscription = check_create_subscription(customer=customer, email=email)

    # Call the checkCreateSubscriptionItem function with the test inputs
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)

    # Call the updateUsage function with the test inputs
    cost = update_usage(subscription_item=subscription_item, bytes=1000)

    # Assert that we captured revenue
    assert cost != 0

    # Assert that there is a customer id
    account = check_customer_account_status(customer=customer)
    assert account['enabled'] is True
    assert account['status'] == 'trial'
    assert account['usage_this_month'] == boost_base_monthly_cost  # first 1 unit is $10 / month


def test_update_usage_base_plus_extra():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # Call the checkCreateCustomer function with the test inputs
    customer = check_create_customer(email=email, org=org)

    # Call the checkCreateSubscription function with the test inputs
    subscription = check_create_subscription(customer=customer, email=email)

    # Call the checkCreateSubscriptionItem function with the test inputs
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)

    # Call the updateUsage function with the test inputs
    extra_units = 4
    cost = update_usage(subscription_item=subscription_item, bytes=(1000 + (extra_units * 1000)))

    # Assert that we captured revenue
    assert cost != 0

    # Assert that there is a customer id
    account = check_customer_account_status(customer=customer)
    assert account['enabled'] is True
    assert account['status'] == 'trial'
    assert account['usage_this_month'] == boost_base_monthly_cost + (extra_units * boost_cost_per_kb)


def test_update_multiple_usage():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # email = 'test-email-ytuvhxcnei@test-org-rvfzgkqtyz.com'
    # org = 'test-org-rvfzgkqtyz'

    first_sub_id = None
    first_item_id = None

    for i in range(0, 10):
        account = check_valid_subscriber(email=email, organization=org, correlation_id="test")

        if first_sub_id is None:
            assert account['usage_this_month'] == 0
        else:
            assert account['usage_this_month'] == boost_base_monthly_cost + (boost_cost_per_kb * (i - 1))

        # Call the updateUsage function with the test inputs
        cost = update_usage(subscription_item=account['subscription_item'], bytes=0)

        account = check_valid_subscriber(email=email, organization=org, correlation_id="test")

        if first_sub_id is None:
            assert account['usage_this_month'] == 0
        else:
            assert account['usage_this_month'] == boost_base_monthly_cost + (boost_cost_per_kb * (i - 1))

        # Call the updateUsage function with the test inputs
        cost = update_usage(subscription_item=account['subscription_item'], bytes=1000)

        first_sub_id = account['subscription']['id'] if first_sub_id is None else first_sub_id
        first_item_id = account['subscription_item']['id'] if first_item_id is None else first_item_id

        assert account['subscription']['id'] == first_sub_id
        assert account['subscription_item']['id'] == first_item_id

        # Assert that we captured revenue
        assert cost != 0

        # simulate a 2nd inbound request
        next_account = check_valid_subscriber(email=email, organization=org, correlation_id="test")

        # assert that we have a combined usage of both costs
        assert next_account['usage_this_month'] > cost

        assert next_account['usage_this_month'] == boost_base_monthly_cost + (boost_cost_per_kb * i)


# now test usage with a large amount to make sure we get charged the right amount
def test_update_usage_large():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    # Call the checkCreateCustomer function with the test inputs
    customer = check_create_customer(email=email, org=org)

    # Call the checkCreateSubscription function with the test inputs
    subscription = check_create_subscription(customer=customer, email=email)

    # Call the checkCreateSubscriptionItem function with the test inputs
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)

    # small amount of data
    oneKb = 1024
    oneDollarInData = 1 / boost_cost_per_kb * oneKb
    trialNinetyNineDollars = 99 * oneDollarInData

    # now check that we correctly flag the customer as active (new account)
    account_status = check_customer_account_status(customer=customer)
    assert account_status['enabled'] is True
    assert account_status['status'] == 'active'
    # Call the updateUsage function with the test inputs
    cost = update_usage(subscription_item=subscription_item, bytes=oneDollarInData)  # small amount of data

    # now check that we correctly flag the customer as in a trial
    account_status = check_customer_account_status(customer=customer)
    assert account_status['enabled'] is True
    assert account_status['status'] == 'trial'
    # Call the updateUsage function with the test inputs
    cost = update_usage(subscription_item=subscription_item, bytes=trialNinetyNineDollars)

    # Assert that the result is revenue
    assert cost != 0
    # Assert that there is a cost object id
    assert subscription_item.id is not None

    # Add a bit more data to go over the trial limit, and require credit card
    cost = update_usage(subscription_item=subscription_item, bytes=oneDollarInData)  # small amount of data

    # now get the current balance from the customer.  we should look up the customer id again to get the latest
    customer = stripe.Customer.retrieve(customer.id)
    assert customer is not None
    assert customer.id is not None
    assert customer.balance is not None

    # now check that we correctly flag the customer as needing to be charged
    account_status = check_customer_account_status(customer=customer)
    assert account_status['enabled'] is False
    assert account_status['status'] == 'expired'

    # get the pending invoice
    invoice = stripe.Invoice.upcoming(customer=customer.id)

    # assert that the invoice is not none
    assert invoice is not None
    assert invoice.amount_due > 0

    # create the credit card for customer
    token = stripe.Token.create(card={
        "number": "4242424242424242",  # Replace with card number
        "exp_month": 12,  # Replace with expiration month
        "exp_year": 2024,  # Replace with expiration year
        "cvc": "123",  # Replace with card CVC
    })
    # attach the card to the customer
    new_source = stripe.Customer.create_source(
        customer.id,
        source=token.id,
    )
    # Set the new card as the default source
    customer = stripe.Customer.modify(
        customer.id,
        default_source=new_source['id']
    )

    # now check that we correctly flag the customer as needing to be charged
    account_status = check_customer_account_status(customer=customer)
    if not account_status['enabled']:
        payment_method = stripe.PaymentMethod.create(
            type='card',
            card={
                'number': '4242424242424242',
                'exp_month': 5,
                'exp_year': 2024,
                'cvc': '314',
            },
        )

        customer = stripe.Customer.modify(
            customer.id,
            invoice_settings={
                'default_payment_method': payment_method.id,
            },
        )

        # now check that we correctly flag the customer as needing to be charged
        account_status = check_customer_account_status(customer=customer)
        assert account_status['enabled'] is True

    assert account_status['status'] == 'paid'

    # remove the card
    stripe.Customer.delete_source(
        customer.id,
        customer.default_source,
    )

    # Retrieve the customer again to get updated data
    customer = stripe.Customer.retrieve(customer.id)

    # now check that we correctly flag the customer as needing to be charged
    account_status = check_customer_account_status(customer=customer)
    assert account_status['enabled'] is False
    assert account_status['status'] == 'expired'


def test_check_valid_subscriber():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    sub = check_valid_subscriber(email=email, organization=org, correlation_id="test")
    assert sub['enabled'] is True


def test_multiple_emails_per_org():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    sub = check_valid_subscriber(email=email, organization=org, correlation_id="test")
    assert sub['enabled'] is True

    email = generate_email("@" + org + ".com")

    sub = check_valid_subscriber(email=email, organization=org, correlation_id="test")
    assert sub['enabled'] is True

    # test a third email
    email = generate_email("@" + org + ".com")

    sub = check_valid_subscriber(email=email, organization=org, correlation_id="test")
    assert sub['enabled'] is True


client_version = '0.9.5'


def test_account_status_unregistered_account():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'foo@bar.test',
            'organization': 'foobar',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'explain', request_body)

        assert response.payload['statusCode'] == 401

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['account']['enabled'] is False
        assert result['account']['status'] == 'unregistered'
        assert result['account']['email'] == 'unknown'
        assert result['account']['org'] == 'foobar'
