import stripe
import argparse
from prettytable import PrettyTable
import os
import sys
import pandas as pd
import datetime
import re
import csv


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


def split_leading_number_from_description(description):
    # Split the string by ' × '
    parts = description.split(' × ')

    # Extract number and plan name
    number = int(parts[0])
    plan = parts[1]
    plan = re.sub(r'^Polyverse Boost \(Tier (.*)\)$', r'T\1', plan)

    return number, plan


def main(show_test, debug, dev, printall, exportcsv, user):

    if not dev:
        os.environ['CHALICE_STAGE'] = 'prod'

    secrets = get_secrets()
    stripe.api_key = secrets['stripe']

    total_pending_invoices = 0
    total_paying_customers = 0
    total_active_users = 0
    total_inactive_users = 0
    total_usage_kb = 0
    total_paid_invoices = 0
    total_customer_discounts = 0

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

            # In your 'Processing customer data' loop, add a check for the user email
            if user and customer.email != user:
                continue

            # exclude any customer with polyverse in email address, unless the command line argument "showTest" is specified
            if ('polyverse' in customer.email or 'test-email-' in customer.email) and not show_test:
                if debug:
                    print(f"Test Account: {customer.email}")
                continue

            print(".", end="")

            invoice = stripe.Invoice.upcoming(customer=customer.id)

            past_invoices = stripe.Invoice.list(customer=customer.id, status='paid')
            customer_paid_invoices = sum([inv.amount_paid for inv in past_invoices])
            customer_discounts = sum(inv.total_discount_amounts[0].amount for inv in past_invoices if inv.total_discount_amounts)
            customer_discounts += invoice.total_discount_amounts[0].amount if invoice.total_discount_amounts else 0

            if debug:
                print(customer)
                print(invoice)

            thisCustomerUsage = 0
            for invoice_data in invoice.lines.data:
                usageInKb, plan_name = split_leading_number_from_description(invoice_data.description)
                thisCustomerUsage += usageInKb

                total_usage_kb += usageInKb

                customers_list.append([customer.metadata.org,
                                       f"{invoice_data.price.metadata.email}",
                                       f"{datetime.datetime.fromtimestamp(customer.created).date()}",
                                       f"{customer.invoice_settings.default_payment_method is not None}",
                                       f"{plan_name}",
                                       f"{usageInKb}",
                                       f"${invoice_data.amount / 100:.2f}",
                                       f"${invoice.amount_due / 100:.2f}",
                                       f"${invoice.total_discount_amounts[0].amount / 100:.2f}" if invoice.total_discount_amounts else "$0.00",
                                       f"${invoice.total / 100:.2f}",
                                       f"${customer_discounts / 100:.2f}",
                                       f"${customer_paid_invoices / 100:.2f}"])

            total_pending_invoices += invoice.amount_due
            total_paid_invoices += customer_paid_invoices
            total_customer_discounts += customer_discounts

            if customer.invoice_settings.default_payment_method:
                total_paying_customers += 1

            if thisCustomerUsage > 0:
                total_active_users += 1
            else:
                total_inactive_users += 1

        except Exception as e:
            if debug:
                print(customer)
            print(f"No upcoming invoice for customer {customer.id} or error fetching invoice: {str(e)}")

    print()

    # customers_list.sort()  # sort by org name

    table = PrettyTable(['Organization', 'Email', 'Created', 'CCard', 'Plan', "Usage", 'Usage(%)', 'Cost', 'Due', 'Trial', 'New', 'Discount', 'Paid'])
    lastCustomerEmail = ''
    lastOrg = ''
    for org, email, created, cc, plan, usageInMb, pending_item_cost, due, discount, total_pending, customer_discounts, total_paid in customers_list:
        newOrg = org != lastOrg
        org = org if org != lastOrg else '"'
        created = created if newOrg else '"'
        email = email if email != lastCustomerEmail else '"'
        lastCustomerEmail = email
        percent = "{:.2f}%".format(int(usageInMb) / total_usage_kb * 100)  # usageInMb is Kb at this point
        percent = percent if percent != '0.00%' else '-'
        usageInMb = "{:.0f} Kb".format((int(usageInMb))) if usageInMb != '0' else '-'
        # usageInMb = "{:.3f} Mb".format((int(usageInMb) / 1024)) if usageInMb != '0' else '-'
        pending_item_cost = pending_item_cost if pending_item_cost != '$0.00' else '-'
        due = due if due != '$0.00' else '-'
        due = due if newOrg and due != '$0.00' else ''
        discount = discount if discount != '$0.00' else '-'
        discount = discount if newOrg else '"'
        total_pending = total_pending if total_pending != '$0.00' else '-'
        total_pending = total_pending if newOrg else ''
        total_paid = total_paid if total_paid != '$0.00' else '-'
        total_paid = total_paid if newOrg else ''
        customer_discounts = customer_discounts if customer_discounts != '$0.00' else '-'
        customer_discounts = customer_discounts if newOrg else ''
        cc = cc if cc != 'False' else ''
        cc = cc if cc != 'True' else 'Yes'
        cc = cc if (newOrg and cc == 'Yes') else ''

        lastOrg = org if org != '"' else lastOrg

        table.add_row([org, email, created, cc, plan, usageInMb, percent, pending_item_cost, due, discount, total_pending, customer_discounts, total_paid])

    if exportcsv:
        csvFile = 'customer_data.csv'
        print(f"Writing CSV file: {csvFile}")
        # If --csv switch is used, write data to CSV instead of table.
        with open(csvFile, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Organization', 'Email', 'Created', 'CCard', 'Plan', "Usage", 'Usage(%)', 'Cost', 'Due', 'Trial', 'New', 'Discounted', 'Paid'])
            for org, email, created, cc, plan, usageInMb, pending_item_cost, due, discount, total_pending, customer_discounts, total_paid in customers_list:
                writer.writerow([org, email, created, cc, plan, usageInMb, percent, pending_item_cost, due, discount, total_pending, customer_discounts, total_paid])
    else:
        # If --csv is not used, print the table.
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
    print(f"\nTotal Paying Customers: {total_paying_customers} - {total_paying_customers / (total_active_users) * 100:.0f}% Converted to Paid")
    print(f"\nTotal Trial Customers: {total_active_users - total_paying_customers} - {(total_active_users - total_paying_customers) / (total_active_users) * 100:.0f}% Active")
    print(f"\nTotal Active Customers: {total_active_users} - {total_active_users / (total_inactive_users + total_active_users) * 100:.0f}%")
    print(f"\nTotal Inactive Customers: {total_inactive_users}")
    print(f"\nTotal Usage (MB): {total_usage_kb / 1024:.2f}")
    print(f"\nTotal Customer Discounts: ${total_customer_discounts / 100:.2f}")
    print(f"\nTotal Paid Invoice Amount for all Customers: ${total_paid_invoices / 100:.2f}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--showTest", action='store_true', help="Include customers with 'polyverse' in their email")
    parser.add_argument("--debug", action='store_true', help="Debug printing")
    parser.add_argument("--printAll", action='store_true', help="Print All Customer data in separate table")
    parser.add_argument("--dev", action='store_true', help="Use Dev Server")
    parser.add_argument("--csv", action='store_true', help="Generate CSV file instead of printing table")
    parser.add_argument("--user", type=str, help="Show invoice data for a single user")
    args = parser.parse_args()

    try:
        main(args.showTest, args.debug, args.dev, args.printAll, args.csv, args.user)
    except KeyboardInterrupt:
        print('Canceling...')
        sys.exit(0)
