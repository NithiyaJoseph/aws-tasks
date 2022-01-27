import json
import boto3, csv, datetime, dateutil.parser, json
from botocore.exceptions import ClientError

iam = boto3.client('iam')
ses = boto3.client('ses', region_name='ap-northeast-1')
sns = boto3.client('sns')

PASSWORD_GRACE_PERIOD = 2
MaxPasswordAge = 1
email_from = "Support <IAM_Access_Password_Check@******.com>"

def lambda_handler(event, context):
    passwordexpireduserlist = {}
    deviationcount = 0
    resp1 = iam.generate_credential_report()
    print (resp1['State'])
    if resp1['State'] == 'COMPLETE' :
        try: 
            response = iam.get_credential_report()
            credential_report_csv = response['Content'].decode("utf-8")
            reader = csv.DictReader(credential_report_csv.splitlines())
            print ("\n***************************************************************")
            print(reader.fieldnames)
            credential_report = []
            for row in reader:
                credential_report.append(row)
            print ("\n****************************************************************")
            print ("\nTotal No. of IAM users:", len(credential_report))
        except ClientError as e:
            print("Unknown error in getting Report: ")
        print ("\n********************************************************************")
        
        
        print ("\nBelow users are having expired password:")
        for row in credential_report:
            if row['password_enabled'] != "true": continue

            last_changed_date=dateutil.parser.parse(row['password_last_changed']).date()
            expires = (last_changed_date + datetime.timedelta(MaxPasswordAge)) - datetime.date.today()
            password_expires = expires.days
            
            if password_expires <= 0:
                print ("\n{}'s Password expired {} days ago".format(row['user'], password_expires * -1))
                passwordexpireduserlist[row['user']] = password_expires * -1
                deviationcount += 1
                user_mail = get_user_tag(row['user'])
                print(user_mail)
                if user_mail != None: 
                    email_alert = ses.send_templated_email(Source=email_from, Destination={'ToAddresses': [user_mail]},Template='SES-TEMPLATE-IAM-Password-Expired',TemplateData=' "password_expires": "password_expires" ')
                else:
                    continue
            
            elif password_expires < PASSWORD_GRACE_PERIOD :
                print ("\n{}'s Password Will expire in {} days".format(row['user'], password_expires))
                #print 'Checking the user tags to find the Mail ID'
                user_mail = get_user_tag(row['user'])
                if user_mail != None:
                    email_alert = ses.send_templated_email(Source=email_from, Destination={'ToAddresses': [user_mail]},Template='SES-TEMPLATE-IAM-Password-Warning',TemplateData=' "password_expires": "password_expires"')
                else:
                    continue
    
    print ("\n**************************************************************************")
    print ("\nTotal No. of users having expired password is:", deviationcount)
    print ("\nPassword Expired User list is below:")
    print (json.dumps(passwordexpireduserlist, indent = 3))
    print ("\n***************************************************************************")
    
    if deviationcount > 0:
        sns.publish(TargetArn='arn:aws:sns:ap-northeast-1:627186023868:demo-12', Subject='IAM Password - Violations', Message=json.dumps({'default': json.dumps(passwordexpireduserlist)}), MessageStructure='json')

    
def get_user_tag(username):        
    tags = iam.list_user_tags(UserName=username)
    #print tags
    mail = None
    if tags['Tags']:
        for tag in tags['Tags']:
            if tag['Key'] == 'mail':
                mail = tag['Value']
                #print('Found user mail ' + mail)
        if mail == None:
            print('Mail Tag is missing for this user')
    else:
        print('\nThis user is not holding any tags\n')
    return (mail)

