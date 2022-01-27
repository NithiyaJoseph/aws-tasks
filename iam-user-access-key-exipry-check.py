import json
from collections import defaultdict
from datetime import datetime, timezone
import logging

import boto3
from botocore.exceptions import ClientError



ALERT_AFTER_N_DAYS = 110

SEND_EVERY_N_DAYS = 3

SES_SENDER_EMAIL_ADDRESS = 'slokesh2912@gmail.com'

SES_REGION_NAME = 'ap-northeast-1'

iam_client = boto3.client('iam')
ses_client = boto3.client('ses', region_name=SES_REGION_NAME)


def is_key_interesting(key):
   
    if key['Status'] != 'Active':
        return False
    
    elapsed_days = (datetime.now(timezone.utc) - key['CreateDate']).days
    
   
    if elapsed_days < ALERT_AFTER_N_DAYS:
        return False
    
    return True

def send_notification(email, keys, account_id):
    email_text = f'''Dear {keys[0]['UserName']},
this is an automatic reminder to rotate your AWS Access Keys at least every {ALERT_AFTER_N_DAYS} days.

At the moment, you have {len(keys)} key(s) on the account {account_id} that have been created more than {ALERT_AFTER_N_DAYS} days ago:
'''
    for key in keys:
        email_text += f"- {key['AccessKeyId']} was created on {key['CreateDate']} ({(datetime.now(timezone.utc) - key['CreateDate']).days} days ago)\n"
    
    email_text += f"""
To learn how to rotate your AWS Access Key, please read the official guide at https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey
If you have any question, please don't hesitate to contact the Support Team at support@example.com.

This automatic reminder will be sent again in {SEND_EVERY_N_DAYS} days, if the key(s) will not be rotated.

Regards,
Your lovely Support Team
"""
    response = ses_client.verify_email_identity(
    EmailAddress = email)
    try:
        ses_response = ses_client.send_email(
            Destination={'ToAddresses': [email ]},
            Message={
                'Body': {'Html': {'Charset': 'UTF-8', 'Data': email_text}},
                'Subject': {'Charset': 'UTF-8',
                            'Data': f'Remember to rotate your AWS Keys on account {account_id}!'}
            },
            Source=SES_SENDER_EMAIL_ADDRESS
        )
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        logging.info(f'Notification email sent successfully to {email}! Message ID: {ses_response["MessageId"]}')

def lambda_handler(event, context):
    users = []
    is_truncated = True
    marker = None
    
    
    while is_truncated:
       
        response = iam_client.list_users(**{k: v for k, v in (dict(Marker=marker)).items() if v is not None})
        users.extend(response['Users'])
        print("response:",response)
        is_truncated = response['IsTruncated']
        marker = response.get('Marker', None)
    
  
    filtered_users = list(filter(lambda u: u.get('PasswordLastUsed'), users))
    
    interesting_keys = []
    
    for user in filtered_users:
        response = iam_client.list_access_keys(UserName=user['UserName'])
        access_keys = response['AccessKeyMetadata']
        
        interesting_keys.extend(list(filter(lambda k: is_key_interesting(k), access_keys)))
    
    interesting_keys_grouped_by_user = defaultdict(list)
    for key in interesting_keys:
        interesting_keys_grouped_by_user[key['UserName']].append(key)

    for keys_for_user in interesting_keys_grouped_by_user.values():
        user_name = keys_for_user[0]['UserName']
        print("inside script:",user_name)
        user_details = iam_client.list_user_tags(UserName=user_name)
        email = None
        print(user_details)
        for tag in user_details.get('Tags', []):
            if tag['Key'] == 'CheckAccessKeyAge':
                email = tag['Value']
                
        if email is None:
            continue
        print("data check:",email)
        print("keys_for_user:",keys_for_user)

        send_notification(email, keys_for_user, context.invoked_function_arn.split(":")[4])
