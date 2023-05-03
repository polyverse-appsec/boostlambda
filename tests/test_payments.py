# test_payments.py
import stripe

# Import the checkCreateCustomer function from the payments module in the chalicelib directory
from chalicelib.payments import check_create_customer, check_create_subscription, check_create_subscription_item, update_usage, check_trial_expired, check_valid_subscriber


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
    result = check_create_customer(email=email, org=org)

    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None

    # now create a second customer with the same email and make sure we get the same customer back
    result2 = check_create_customer(email=email, org=org)
    assert result2 is not None
    assert result2.id is not None
    assert result2.id == result.id

    # now create a third customer with a different email and the same org and make sure we get the same customer back
    email2 = generate_email("@" + org + ".com")
    result3 = check_create_customer(email=email2, org=org)
    assert result3 is not None
    assert result3.id is not None
    assert result3.id == result.id

    # now create a fourth customer with a different email and a different org and make sure we get a different customer back
    org2 = generate_org()
    email3 = generate_email("@" + org2 + ".com")
    result4 = check_create_customer(email=email3, org=org2)
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


def test_update_usage():
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
    result = update_usage(subscription_item=subscription_item, bytes=1000)

    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None


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

    # now check that we correctly flag the customer as in a trial
    expired = check_trial_expired(customer=customer)
    assert expired is False
    # Call the updateUsage function with the test inputs
    result = update_usage(subscription_item=subscription_item, bytes=104857600)

    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None

    # now get the current balance from the customer.  we should look up the customer id again to get the latest
    customer = stripe.Customer.retrieve(customer.id)
    assert customer is not None
    assert customer.id is not None
    assert customer.balance is not None

    # now check that we correctly flag the customer as needing to be charged
    expired = check_trial_expired(customer=customer)
    assert expired is True

    # get the pending invoice
    invoice = stripe.Invoice.upcoming(customer=customer.id)

    # assert that the invoice is not none
    assert invoice is not None
    assert invoice.amount_due > 0


def test_check_valid_subscriber():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    valid, sub = check_valid_subscriber(email=email, organization=org)
    assert valid is True
    assert sub is not None


def test_multiple_emails_per_org():
    # Define test inputs
    org = generate_org()
    email = generate_email("@" + org + ".com")

    valid, sub = check_valid_subscriber(email=email, organization=org)
    assert valid is True
    assert sub is not None

    email = generate_email("@" + org + ".com")

    valid, sub = check_valid_subscriber(email=email, organization=org)
    assert valid is True
    assert sub is not None

    # test a third email
    email = generate_email("@" + org + ".com")

    valid, sub = check_valid_subscriber(email=email, organization=org)
    assert valid is True
    assert sub is not None
