# test_payments.py
import stripe

# Import the checkCreateCustomer function from the payments module in the chalicelib directory
from chalicelib.payments import check_create_customer, check_create_subscription, check_create_subscription_item, update_usage, check_trial_expired

# utility function to generate an org name with a random domain
def generation_org():
    import random
    import string
    # Generate a random string of 10 lowercase letters for the domain
    org = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
    return org

def generate_email(domain):
    import random
    import string
    # Generate a random string of 10 lowercase letters for the domain
    return ''.join(random.choice(string.ascii_lowercase) for i in range(10)) + domain


# Define a test function using the pytest naming convention (test_*)
def test_check_create_customer():
    # Define test inputs
    org = generation_org()
    email = generate_email("@" + org + ".com")
    
    # Call the checkCreateCustomer function with the test inputs
    result = check_create_customer(email=email, org=org)
    
    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None
    
def test_check_create_subscription():
    # Define test inputs
    org = generation_org()
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
    org = generation_org()
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
    org = generation_org()
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

#now test usage with a large amount to make sure we get charged the right amount
def test_update_usage_large():
    # Define test inputs
    org = generation_org()
    email = generate_email("@" + org + ".com")
    
    # Call the checkCreateCustomer function with the test inputs
    customer = check_create_customer(email=email, org=org)
    
    # Call the checkCreateSubscription function with the test inputs
    subscription = check_create_subscription(customer=customer, email=email)
    
    # Call the checkCreateSubscriptionItem function with the test inputs
    subscription_item = check_create_subscription_item(subscription=subscription, email=email)
    
    #now check that we correctly flag the customer as in a trial
    expired = check_trial_expired(customer=customer)
    assert expired is False
    # Call the updateUsage function with the test inputs
    result = update_usage(subscription_item=subscription_item, bytes=104857600)
    
    # Assert that the result is a customer object
    assert result is not None
    # Assert that there is a customer id
    assert result.id is not None    

    #now get the current balance from the customer.  we should look up the customer id again to get the latest
    customer = stripe.Customer.retrieve(customer.id)
    print(customer)
    assert customer is not None
    assert customer.id is not None
    assert customer.balance is not None

    #now check that we correctly flag the customer as needing to be charged
    expired = check_trial_expired(customer=customer)
    assert expired is True

    #get the pending invoice
    invoice = stripe.Invoice.upcoming(customer=customer.id)

    #assert that the invoice is not none
    assert invoice is not None
    assert invoice.amount_due > 0
    print (invoice)

  