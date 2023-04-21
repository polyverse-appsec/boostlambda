import stripe
from . import pvsecret

secret_json = pvsecret.get_secrets()

stripe.api_key = secret_json["stripe"]
print("stripe key ", secret_json["stripe"])

# a function to call stripe to create a customer
def check_create_customer(email, org):
    customer = stripe.Customer.create(
        email=email,
        name=org,
        metadata={"org": org},
    )
    return customer

