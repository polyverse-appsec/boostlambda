import stripe
from . import pvsecret

secret_json = pvsecret.get_secrets()

stripe.api_key = secret_json["stripe"]
print("stripe key ", secret_json["stripe"])

# a function to call stripe to create a customer
def check_create_customer(email, org):
    #first see if the customer already exists, we need to look at the org field in metadata
    customers = stripe.Customer.search(query='metadata["org"]: "{}"'.format(org))
                                     
    for customer in customers.data:
        if customer.metadata.org == org:
            return customer

    customer = stripe.Customer.create(
        email=email,
        metadata={"org": org},
    )
    return customer

