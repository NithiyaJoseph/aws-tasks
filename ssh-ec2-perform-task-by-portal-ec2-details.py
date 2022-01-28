import json
import boto3
import paramiko
from pprint import pprint
import string
import random
import time
from botocore.exceptions import ClientError


global resource_name,region_name, pubipaddress,client_info,ec2,desc_instance,tags_test,volumeids,avaliablity_zone,instanceids,instanceid_info,instances
global volume,ids_volu,display_volume,description,groupname
ids_volu=[]
volume=[]
instances=[]
instanceid_info=[]
instanceids=[]
avaliablity_zone=[]
volumeids=[]
resource_name='ec2'
region='ap-northeast-1'
pubipaddress=[]
display_volume=[]
client_info=[]
desc_instance=[]
ec2=boto3.client(resource_name,region_name=region)
tags_test={'Name':'tag:test-env','Values':['yes']}

ec2_resource = boto3.resource('ec2', region_name=region)

description= 'Security group created test '
groupname = 'cloud-security-group'
    

def get_instance_info(pubipaddress,instanceids):
    desc_instance=ec2.describe_instances()
    for instance in desc_instance['Reservations']:
        for inst_state in instance['Instances']:
            if inst_state['State']['Name'] == 'running':
                pubipaddress.append(inst_state['PublicIpAddress'])
                instanceids.append(inst_state['InstanceId'])
            else:
                print("No instance running in these region")
    print("method values print:",pubipaddress,instanceids) 
    return pubipaddress,instanceids
    
def ssh_client_connect(client_info):
    
    host,instanceid_info=get_instance_info(pubipaddress,instanceids)
    print("ssh:",host)
    
    s3_client = boto3.client("s3")
    s3_client.download_file("rekognit123", "lokesh-new-key.pem", "/tmp/file.pem")
    print("pem file downloaded successfully!!! to local path")

    key = paramiko.RSAKey.from_private_key_file("/tmp/file.pem")
    
    ssh_client = paramiko.SSHClient()
 
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    host = pubipaddress[0]
    print("Connecting to : " + host)
    
    ssh_client.connect(hostname=host,username="root", password="1234")
    print("Connected to :" + host)
    
    commands = ["ls"]
    
    for command in commands:
        print("Executing:" ,command)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print(stderr.read())
    return stdout.read()

    

def instance_volume_creation(volumeids):
    response = ec2.create_volume(
    AvailabilityZone='ap-northeast-1c',
    Encrypted=False,
    Size=8,
    VolumeType='gp2',
    TagSpecifications=[
        {
            'ResourceType': 'volume',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'demovolume'
                },
            ]
        },
    ],)
    volumeids.append(response['VolumeId'])
    print("checking:",volumeids)
    return volumeids
    
def volume_attach():
    print("data volume attach:",instanceids,volumeids)
    volid=''.join(volumeids)
    print(type(volid))
    
    str1='sd'
    string.ascii_letters
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' 
    character=random.choice(string.ascii_letters)
    device_name="".join([str1,character.lower()])  
    print(device_name)
    
    dev_str='/dev/'
    device_nm="".join([dev_str,device_name])
    
    instances=instanceids[0]
    volid=volumeids[0]
    
    volumes = ec2_resource.Volume(volid)
    instances=instanceids[0]
    print(f'Volume {volumes.id} status -> {volumes.state}')
    
    time.sleep(30)
    
    volumes.attach_to_instance(
    Device=device_nm,
    InstanceId=instances,
    VolumeId=volid)
    print(f'Volume {volumes.id} status -> {volumes.state}')
    print("volume attached successfully!!!")

def listing_volumes(ids_volu):
    ec2 = boto3.resource(resource_name, region_name=region)
    for volume in ec2.volumes.all():
        print(f'volume {volume.id} ({volume.size} GIB ) -> {volume.state}')
        display_volume.append(volume)
        
def detach_volume():
    print(ids_volu)
    
    '''
    volumes = ec2_resource.Volume(volm)
    volumes.detach_from_instance(
    Device='/dev/sdf',
    InstanceId=instances,
    VolumeId=volm)
    print(f'Volume {volumes.id} status -> {volumes.state}')
    print("volume dettached  successfully!!!")
    '''

def security_group():
    try:
        response = ec2.create_security_group(
        Description=description,
        GroupName=groupname,
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'task2-security'
                    },
                ]
            },],)
        security_group_id = response['GroupId']
        pprint(f'securityid-> {security_group_id}')
        
        data = ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        
        IpPermissions=[
            {
             'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                
            },
            {
             'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                
            }
        ])
        pprint("Ingress Successfully Set ",data)
    
    
    
    except ClientError as e:
        print(e)
    

 
    
    
def lambda_handler(event, context):
    # TODO implement
    print("-"*60)

    client_login_info=ssh_client_connect(client_info)
    print("client  stdout info:",client_login_info)
    print("-"*60)
    '''
    instance_volume_creation(volumeids)

    volume_attach()
    '''
    detach_volume()
    listing_volumes(ids_volu)
    security_group()
    
