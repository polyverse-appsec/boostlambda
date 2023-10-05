import boto3
from botocore.exceptions import ClientError


def send_email(subject, body, recipient_email, sender_email="boost-cloud-service@polytest.ai"):
    if recipient_email == "":
        print(f"SIMULATING SES EMAIL (blank recipient): {subject}")
        return

    client = boto3.client('ses')
    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [recipient_email],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': body,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject,
                },
            },
            Source=sender_email,
        )
    except ClientError as e:
        print(f"Boost Service Send Email failed from {send_email} to {recipient_email}: {e.response['Error']['Message']}")
    else:
        print(f"SES Email (id:{response['MessageId']}) sent to {recipient_email}: {subject}")
