from chalicelib.email import send_email
import os

test_email = "stephen@polyverse.com"
dev_email = test_email
production_email = "support@polyverse.com"

alert_sender_email = "stephen@polyverse.com"

# don't alert on any activity from this domain
alert_bypass_domain = "polytest.ai"

service_stage = os.environ.get('CHALICE_STAGE', 'local')

if 'AWS_CHALICE_CLI_MODE' not in os.environ and 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    if service_stage in ('dev', 'test'):
        notify_recipients = dev_email
    elif service_stage in ('staging', 'prod'):
        notify_recipients = production_email
else:
    # when doing local debugging, don't send email (by default)
    # otherwise, we'll get buried on test emails from test automation
    notify_recipients = test_email if service_stage != 'local' else ""

# only send email if EMAIL_NOTIFICATIONS is set in env variable - otherwise, clear notify_recipients and log
if 'EMAIL_NOTIFICATIONS' not in os.environ:
    notify_recipients = ""
    print("NOT sending alert email (EMAIL_NOTIFICATIONS not set in env variable)")


def notify_email(email, org, subject, body=""):
    alert_bypassed = (alert_bypass_domain in org or alert_bypass_domain in email)

    if not notify_recipients or notify_recipients == "":
        print(f"NOT sending alert email for {subject} to {email} for {org} (notification email not set)")
        return

    if body:
        body = f"\n\n{body}"

    try:
        send_email(
            subject=f"{subject}: {org}",
            body=f"{subject}:\n  Email: {email}\n  Org: {org}{body}",
            recipient_email=(notify_recipients if not alert_bypassed else ""),
            sender_email=alert_sender_email)
    except Exception as e:
        print(f"Failed to send alert email for {subject} to {email} for {org}: {e}")


def notify_new_customer(email, org):
    notify_email(
        email,
        org,
        "New Customer")


def notify_customer_first_usage(email, org, usage_type):
    notify_email(
        email,
        org,
        "First Customer Usage",
        f"  Usage Type: {usage_type}")
