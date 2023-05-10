import os
import sys
import stripe

# Get the Stripe API key from the environment variable
stripe.api_key = os.getenv("STRIPE_API_KEY")

def get_upcoming_invoice(customer_id):
    try:
        invoice = stripe.Invoice.upcoming(customer=customer_id)
        return invoice
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py customer_id")
        return

    customer_id = sys.argv[1]
    invoice = get_upcoming_invoice(customer_id)

    if invoice is not None:
        print(f"Upcoming invoice for customer {customer_id}:")
        print(invoice)

if __name__ == "__main__":
    main()
