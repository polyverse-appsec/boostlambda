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
    # when doing local debugging, don't send email (by default)
    # otherwise, we'll get buried on test emails from test automation
    notify_recipients = test_email if service_stage != 'local' else ""


def notify_new_customer(email, org):
    send_email(
        subject=f"New Customer: {org}",
        body=f"New Customer:\n  Email: {email}\n  Org: {org}",
        recipient_email=notify_recipients,
        sender_email=alert_sender_email)


def notify_customer_first_usage(email, org, usage_type):
    send_email(
        subject=f"Customer First Usage: {org}",
        body=f"Customer First Usage:\n  Email: {email}\n  Org: {org}\n  Usage Type: {usage_type}",
        recipient_email=notify_recipients,
        sender_email=alert_sender_email)
