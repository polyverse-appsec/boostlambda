import stripe
import argparse
from prettytable import PrettyTable
import os
import sys
import pandas as pd
import datetime

# Determine the parent directory's path.
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append the parent directory to sys.path.
sys.path.append(parent_dir)

from chalicelib.pvsecret import get_secrets # noqa


def extract_values(obj, key):
    """Pull all values of specified key from nested Python dictionary."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in dictionary."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results


def main(show_test, debug, dev, printall):

    if not dev:
        os.environ['CHALICE_STAGE'] = 'prod'

    secrets = get_secrets()
    stripe.api_key = secrets['stripe']

    total_pending_invoices = 0
    total_paying_customers = 0
    print("Retrieving Boost customer list")
    customers = stripe.Customer.list()
    customers_list = []
    customer_iter = customers.auto_paging_iter()

    print("Processing customer data")
    for customer in customer_iter:
        try:
            # if there is no metadata field or the field org does not exist, skip this customer
            if 'metadata' not in customer or 'org' not in customer.metadata:
                # if debug:
                #     print(f"Non-Boost Customer: {customer.email}")
                continue

            # exclude any customer with polyverse in email address, unless the command line argument "showTest" is specified
            if ('polyverse' in customer.email or 'test-email-' in customer.email) and not show_test:
                if debug:
                    print(f"Test Account: {customer.email}")
                continue

            print(".", end="")

            invoice = stripe.Invoice.upcoming(customer=customer.id)
            if debug:
                print(customer)
                print(invoice)

            firstName = True
            for invoice_data in invoice.lines.data:
                if firstName:
                    customers_list.append([customer.metadata.org,
                                           f"{invoice_data.price.metadata.email}",
                                           f"${invoice.amount_due / 100:.2f}",
                                           f"{customer.invoice_settings.default_payment_method is not None}",
                                           f"{invoice_data.discount_amounts[0].amount / 100:.2f}",
                                           f"{datetime.datetime.fromtimestamp(customer.created)}"])
                    firstName = False
                else:
                    customers_list.append(['"',
                                           f"{invoice_data.price.metadata.email}",
                                           '"',
                                           '"',
                                           f"{invoice_data.discount_amounts[0].amount / 100:.2f}",
                                           '"'])

            total_pending_invoices += invoice.amount_due
            if customer.invoice_settings.default_payment_method:
                total_paying_customers += 1

        except Exception as e:
            if debug:
                print(customer)
            print(f"No upcoming invoice for customer {customer.id} or error fetching invoice: {str(e)}")

    print()

    # customers_list.sort()  # sort by org name

    table = PrettyTable(['Organization', 'Email', 'Pending Invoice Amount', 'Credit Card', 'Discount', 'Created'])
    for org, email, amount, cc, discount, created in customers_list:
        table.add_row([org, email, amount, cc, discount, created])

    print(table)
    print()

    # print all customer data record fields
    if printall:
        # Convert iterable of Customer objects to list of dictionaries
        customers_dict_list = [customer.to_dict() for customer in customers]

        pd.set_option('display.max_columns', None)  # None means unlimited.
        pd.set_option('display.max_colwidth', 25)  # Adjust as needed.

        # Create a pandas DataFrame from the list of dictionaries
        df = pd.json_normalize(customers_dict_list)

        # Set 'email' column as the first column
        column_order = ['email'] + [col for col in df.columns if col != 'email']
        df = df[column_order]

        print(df)

    print()
    print(f"\nTotal Pending Invoice Amount for all Customers: ${total_pending_invoices / 100:.2f}")
    print(f"\nTotal Paying Customers: {total_paying_customers}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--showTest", action='store_true', help="Include customers with 'polyverse' in their email")
    parser.add_argument("--debug", action='store_true', help="Debug printing")
    parser.add_argument("--printAll", action='store_true', help="Print All Customer data in separate table")
    parser.add_argument("--dev", action='store_true', help="Use Dev Server")
    args = parser.parse_args()

    try:
        main(args.showTest, args.debug, args.dev, args.printAll)
    except KeyboardInterrupt:
        print('Canceling...')
        sys.exit(0)
