import logging 
          import cfnresponse
          import json
          import boto3
          from threading import Timer
          from botocore.exceptions import WaiterError

          logger = logging.getLogger()
          logger.setLevel(logging.INFO)

          def handler(event, context):

              ec2 = boto3.resource('ec2')
              physicalId = event['PhysicalResourceId'] if 'PhysicalResourceId' in event else None

              def success(data={}):
                cfnresponse.send(event, context, cfnresponse.SUCCESS, data, physicalId)

              def failed(e):
                cfnresponse.send(event, context, cfnresponse.FAILED, str(e), physicalId)

              logger.info('Request received: %s\n' % json.dumps(event))

              try:
                instanceId = event['ResourceProperties']['InstanceId']
                if (not instanceId):
                  raise 'InstanceID required'

                if not 'RequestType' in event:
                  success({'Data': 'Unhandled request type'})
                  return

                if event['RequestType'] == 'Delete':
                  if (not physicalId.startswith('ami-')):
                    raise 'Unknown PhysicalId: %s' % physicalId

                  ec2client = boto3.client('ec2')
                  images = ec2client.describe_images(ImageIds=[physicalId])
                  for image in images['Images']:
                    ec2.Image(image['ImageId']).deregister()
                    snapshots = ([bdm['Ebs']['SnapshotId'] 
                                  for bdm in image['BlockDeviceMappings'] 
                                  if 'Ebs' in bdm and 'SnapshotId' in bdm['Ebs']])
                    for snapshot in snapshots:
                      ec2.Snapshot(snapshot).delete()

                  success({'Data': 'OK'})
                elif event['RequestType'] in set(['Create', 'Update']):
                  if not physicalId:  # AMI creation has not been requested yet
                    instance = ec2.Instance(instanceId)
                    instance.wait_until_stopped()

                    image = instance.create_image(Name="Automatic from CloudFormation stack ${AWS::StackName}")

                    physicalId = image.image_id
                  else:
                    logger.info('Continuing in awaiting image available: %s\n' % physicalId)

                  ec2client = boto3.client('ec2')
                  waiter = ec2client.get_waiter('image_available')

                  try:
                    waiter.wait(ImageIds=[physicalId], WaiterConfig={'Delay': 30, 'MaxAttempts': 6})
                  except WaiterError as e:
                  # Request the same event but set PhysicalResourceId so that the AMI is not created again
                    event['PhysicalResourceId'] = physicalId
                    logger.info('Timeout reached, continuing function: %s\n' % json.dumps(event))
                    lambda_client = boto3.client('lambda')
                    lambda_client.invoke(FunctionName=context.invoked_function_arn, 
                                          InvocationType='Event',
                                          Payload=json.dumps(event))
                    return

                  success({'Data': 'OK'})
                else:
                  success({'Data': 'OK'})
            except Exception as e:
              failed(e)

