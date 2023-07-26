import stripe
import argparse
from prettytable import PrettyTable
import os
import sys
import pandas as pd
import datetime
import re
import csv
import traceback


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
    plan = re.sub(r'Polyverse Boost \((?:Tier (\d) )?at \$(.+) \/ month\)', r'T\1 at $\2', plan)

    return number, plan


def main(show_test, debug, dev, printall, exportcsv, user, includePolyverse):

    if not dev:
        os.environ['CHALICE_STAGE'] = 'prod'

    secrets = get_secrets()
    stripe.api_key = secrets['stripe']

    from chalicelib.payments import check_customer_account_status # noqa

    total_pending_invoices = 0

    total_paying_customers = 0
    total_active_users = 0
    total_inactive_users = 0
    total_suspended_customers = 0

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
            if user and user != "*" and user not in customer.email:
                print("-", end="")
                continue

            # exclude any customer with test email in email address, unless the command line argument "showTest" is specified
            if ('test-email-' in customer.email) and not show_test:
                if debug:
                    print(f"Test Account: {customer.email}")

                print("-", end="")
                continue

            # exclude polyverse accounts (dev and test) unless specifically requested
            if ('polyverse' in customer.email or 'polytest.ai' in customer.email) and not includePolyverse:
                if debug:
                    print(f"Test Account: {customer.email}")
                print("-", end="")
                continue

            print(".", end="")

            upcoming_invoice = stripe.Invoice.upcoming(customer=customer.id) if \
                len(stripe.Subscription.list(customer=customer.id)['data']) > 0 \
                and not customer.delinquent else None

            past_invoices = stripe.Invoice.list(customer=customer.id, status='paid')
            open_invoices = stripe.Invoice.list(customer=customer.id, status='open')
            void_invoices = stripe.Invoice.list(customer=customer.id, status='void')
            draft_invoices = stripe.Invoice.list(customer=customer.id, status='draft')

            all_invoices = past_invoices.data + open_invoices.data + void_invoices.data + draft_invoices.data  # + ([upcoming_invoice] if upcoming_invoice else [])
            if debug:
                print(f"{customer.email} has {len(all_invoices)} invoices")

            if customer.delinquent and debug:
                print(f"\nSkipping reporting for Delinquent customer: {customer.email}\n")

            customer_paid_invoices = sum([inv.amount_paid for inv in past_invoices])
            customer_discounts = sum(inv.total_discount_amounts[0].amount for inv in past_invoices if inv.total_discount_amounts)
            customer_discounts += upcoming_invoice.total_discount_amounts[0].amount if (upcoming_invoice and upcoming_invoice.total_discount_amounts) else 0

            if debug:
                print(customer)
                print(upcoming_invoice if upcoming_invoice else "No upcoming invoice")

            _, account_status = check_customer_account_status(customer)

            thisCustomerUsage = 0
            targetInvoices = ([upcoming_invoice] if upcoming_invoice else []) + list(past_invoices) + list(open_invoices)

            total_pending_invoices += upcoming_invoice.amount_due if upcoming_invoice else 0
            total_paid_invoices += customer_paid_invoices
            total_customer_discounts += customer_discounts
            total_suspended_customers += 1 if customer.delinquent else 0
            if customer.invoice_settings.default_payment_method:
                total_paying_customers += 1

            for invoice in targetInvoices:
                for invoice_data in invoice.lines.data:
                    usageInKb, plan_name = split_leading_number_from_description(invoice_data.description)
                    thisCustomerUsage += usageInKb

                    total_usage_kb += usageInKb

                    open_credit = customer['discount']['coupon']['amount_off'] if \
                        customer['discount'] and customer['discount']['coupon'] and \
                        customer['discount']['coupon']['amount_off'] else 0

                    customers_list.append([customer.metadata.org,
                                           f"{invoice_data.price.metadata.email}",
                                           f"{datetime.datetime.fromtimestamp(customer.created).date()}",
                                           f"{account_status}",
                                           f"{customer.invoice_settings.default_payment_method is not None}",
                                           f"{plan_name}",
                                           f"{usageInKb}",
                                           f"${invoice_data.amount / 100:.2f}",
                                           f"${invoice.amount_due / 100:.2f}",
                                           f"${open_credit / 100:.2f}",
                                           f"${invoice.total / 100:.2f}",
                                           f"${customer_discounts / 100:.2f}",
                                           f"${customer_paid_invoices / 100:.2f}"])

            if thisCustomerUsage > 0:
                total_active_users += 1
            else:
                total_inactive_users += 1

        except Exception:
            if debug:
                print(customer)

            print(f"No upcoming invoice for customer {customer.id} or error fetching invoice: {str(traceback.format_exc())}")

    if total_active_users == 0:
        print("\n\nNo customers found", end="")
        print(f" - user: {user}" if user else "\n\n")
        exit(1)

    print()
    print("-------------------------------------------------------------------")
    print(f"Invoice Report Date/Time: {datetime.datetime.now().strftime('%B %d, %Y, %I:%M:%S %p')}")
    print("-------------------------------------------------------------------")

    if exportcsv:
        csvFile = 'customer_data.csv'
        print(f"Writing CSV file: {csvFile}")
        # If --csv switch is used, write data to CSV instead of table.
        with open(csvFile, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Organization', 'Email', 'Created', 'Status', 'CCard', 'Plan', "Usage", 'Usage(%)', 'Cost', 'Due', 'Trial', 'New', 'Discounted', 'Paid'])
            for org, email, created, status, cc, plan, usageInMb, percent, pending_item_cost, due, open_credit, total_pending, customer_discounts, total_paid in customers_list:
                writer.writerow([org, email, created, cc, plan, usageInMb, percent, pending_item_cost, due, open_credit, total_pending, customer_discounts, total_paid])
    else:

        # customers_list.sort()  # sort by org name
        total_coupons = 0

        table = PrettyTable(['Organization', 'Email', 'Created', 'Status', 'CCard', 'Plan', "Usage", 'Usage(%)', 'Cost', 'Due', 'Trial', 'New', 'Discount', 'Paid'])
        lastCustomerEmail = ''
        lastOrg = ''
        for org, email, created, status, cc, plan, usageInMb, pending_item_cost, due, discount, total_pending, customer_discounts, total_paid in customers_list:
            newOrg = org != lastOrg
            org = org if org != lastOrg else '"'
            created = created if newOrg else '"'
            email = email if org != lastOrg and email != lastCustomerEmail else '"'
            lastCustomerEmail = email if email != '"' else lastCustomerEmail
            percent = "{:.2f}%".format(((int(usageInMb) / total_usage_kb) if total_usage_kb > 0 else 0) * 100)  # usageInMb is Kb at this point
            percent = percent if percent != '0.00%' else '-'
            usageInMb = "{:.0f} Kb".format((int(usageInMb))) if usageInMb != '0' else '-'
            # usageInMb = "{:.3f} Mb".format((int(usageInMb) / 1024)) if usageInMb != '0' else '-'
            pending_item_cost = pending_item_cost if pending_item_cost != '$0.00' else '-'
            due = due if due != '$0.00' else '-'
            due = due if newOrg and due != '$0.00' else ''
            discount = discount if discount != '0' else '-'
            discount = discount if newOrg else '"'
            total_coupons += float(discount[1:]) * 100 if (discount != "-" and discount != '"') else 0
            total_pending = total_pending if total_pending != '$0.00' else '-'
            total_pending = total_pending if newOrg else ''
            total_paid = total_paid if total_paid != '$0.00' else '-'
            total_paid = total_paid if newOrg else ''
            customer_discounts = customer_discounts if customer_discounts != '$0.00' else '-'

            status = status if newOrg else ''
            customer_discounts = customer_discounts if newOrg else ''
            cc = cc if cc != 'False' else ''
            cc = cc if cc != 'True' else 'Yes'
            cc = cc if (newOrg and cc == 'Yes') else ''

            lastOrg = org if org != '"' else lastOrg

            if len(org) > 20:
                shortOrg = org[:20] + "..."
            else:
                shortOrg = org
            table.add_row([shortOrg, email, created, status, cc, plan, usageInMb, percent, pending_item_cost, due, discount, total_pending, customer_discounts, total_paid])

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
        totalTable = PrettyTable(['Total Revenue', 'Amount', '%'])
        total_overall = total_pending_invoices + total_paid_invoices + total_customer_discounts
        totalTable.add_row(["DUE Amount (All Customer Invoices)", f"${total_pending_invoices / 100:.2f}", f"{((total_pending_invoices / total_overall) if total_overall > 0 else 0) * 100:.0f}%"])
        totalTable.add_row(["PAID Amount (All Customer Invoices)", f"${total_paid_invoices / 100:.2f}", f"{((total_paid_invoices / total_overall) if total_overall > 0 else 0) * 100:.0f}%"])
        totalTable.add_row(["COUPON (Active) Amount (All Customer Invoices)", f"${total_coupons / 100:.2f}", f"{((total_coupons / total_overall) if total_overall > 0 else 0) * 100:.0f}%"])
        totalTable.add_row(["DISCOUNTED Amount (All Customer Invoices)", f"${total_customer_discounts / 100:.2f}", f"{((total_customer_discounts / total_overall) if total_overall > 0 else 0) * 100:.0f}%"])
        totalTable.add_row(["-------------------------------------------", "---------", "-----"])
        totalTable.add_row(["TOTAL Revenue/Usage (All Customer Invoices)", f"${total_overall / 100:.2f}", ""])
        print(totalTable)
        print()

        customerTable = PrettyTable(['Total Customers', 'Amount', "%"])
        total_users = total_active_users + total_inactive_users
        customerTable.add_row(["Paying Customers", f"{total_paying_customers}", f"{(total_paying_customers / total_active_users) if total_active_users > 0 else 0 * 100:.0f}% Converted"])
        customerTable.add_row(["Trial Customers", f"{total_active_users - total_paying_customers}", f"{((total_active_users - total_paying_customers) / total_active_users) if total_active_users > 0 else 0 * 100:.0f}% of Active"])
        customerTable.add_row(["Active Customers", f"{total_active_users}", f"{(total_active_users / total_users) if total_users > 0 else 0 * 100:.0f}% of Total"])
        customerTable.add_row(["New Customers", f"{total_inactive_users}", f"{(total_inactive_users / total_users) if total_users > 0 else 0 * 100:.0f}% of Total"])
        customerTable.add_row(["Suspended Customers", f"{total_suspended_customers}", f"{(total_suspended_customers / total_users) if total_users > 0 else 0 * 100:.0f}% of Total"])
        customerTable.add_row(["----------------------", "-----", "-----------"])
        customerTable.add_row(["TOTAL Customers", f"{total_users}", ""])
        print(customerTable)
        print()

        usageTable = PrettyTable(['Usage', 'Amount'])
        usageTable.add_row(["Total (MB)", f"{total_usage_kb / 1024:.2f}mb"])
        print(usageTable)
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--showTest", action='store_true', help="Include customers with 'polyverse' in their email")
    parser.add_argument("--debug", action='store_true', help="Debug printing")
    parser.add_argument("--printAll", action='store_true', help="Print All Customer data in separate table")
    parser.add_argument("--dev", action='store_true', help="Use Dev Server")
    parser.add_argument("--csv", action='store_true', help="Generate CSV file instead of printing table")
    parser.add_argument("--user", type=str, help="Show invoice data for a single user")
    parser.add_argument("--includePolyverse", action='store_true', help="Include Polyverse account data")
    args = parser.parse_args()

    try:
        main(args.showTest, args.debug, args.dev, args.printAll, args.csv, args.user, args.includePolyverse)
    except KeyboardInterrupt:
        print('Canceling...')
        sys.exit(0)
