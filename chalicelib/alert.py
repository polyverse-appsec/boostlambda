from chalicelib.email import send_email
import os

test_email = "stephen@polyverse.com"
dev_email = test_email
production_email = "support@polyverse.com"

alert_sender_email = "stephen@polyverse.com"

service_stage = os.environ.get('CHALICE_STAGE', 'local')

if 'AWS_CHALICE_CLI_MODE' not in os.environ and 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    if service_stage in ('dev', 'test'):
        notify_recipients = dev_email
    elif service_stage == ('staging', 'prod'):
        notify_recipients = production_email
else:
    notify_recipients = test_email


def notify_new_customer(email, org):
    send_email(
        subject=f"New Customer: {org}",
        body=f"New Customer:\n  Email: {email}  \nOrg: {org}",
        recipient_email=notify_recipients,
        sender_email=alert_sender_email)


def notify_customer_first_usage(customer):
    send_email(
        subject=f"Customer First Usage: {customer['name']}",
        body=f"Customer First Usage: {customer['name']}\n\n{customer}",
        recipient_email=notify_recipients,
        sender_email=alert_sender_email)