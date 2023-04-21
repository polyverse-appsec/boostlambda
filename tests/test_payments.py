# test_payments.py

# Import the checkCreateCustomer function from the payments module in the chalicelib directory
from chalicelib.payments import check_create_customer

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
    