"""
Filename:       bran.py
Author(s):      Nihal Dhamani
Contact:        nihaldhamani@gmail.com
Date Modified:  3/26/19

Bran is used as a cli to automatically create and ssh into an ec2 instance 
given user input settings. Bran automatically sets up the docker container 
needed to run raven.
"""
import boto3
from botocore.exceptions import ClientError
import os
from random import randint
import subprocess
import time
from progress.spinner import Spinner
import pyperclip
from PyInquirer import style_from_dict, Token, prompt
from PyInquirer import Validator, ValidationError
from boto.s3.key import Key
import configparser
from os.path import expanduser
import tempfile

def get_local_awsconfig():
    """
    Gets the aws credentials stored on the local machine. The AWSCLI configuration 
    command stores credentials at ~/.aws/credentials which are accessed and convereted
    into a dictionary.

    Return:
        aws_config (dictionary): a dictionary containing aws_access_key_id,
            aws_secret_access_key, region, and output
    """

    home = expanduser("~")
    config = configparser.ConfigParser()
    aws_config = {}
    config.read(home + '/.aws/credentials')
    aws_config['key_id'] = config['default']['aws_access_key_id']
    aws_config['secret_key'] = config['default']['aws_secret_access_key']
    config.read(home + '/.aws/config')
    aws_config['region'] = config['default']['region']
    aws_config['output'] = config['default']['output']

    return aws_config

def list_to_choices(l):
    """
    Converts a python list to choices for PyInquirer question prompts.

    Args:
        l (list): a python list
    
    Return:
        choices ([dicts]): a list of dictionaries
    """
    l = sorted(l)[::-1]
    choices = []
    for item in l:
        choices.append({'name': item})
    return choices

def get_security_groups():
    """
    Gets all available AWS security group names and ids associated with an AWS role.

    Return:
        sg_names (list): list of security group id, name, and description
    """
    sg_groups = boto3.client('ec2', region_name='us-west-1').describe_security_groups()['SecurityGroups']
    sg_names = []
    for sg in sg_groups:
        sg_names.append(sg['GroupId'] + ': ' + sg['GroupName'] + ': ' + sg['Description'])

    return sg_names


def get_questions():
    """
    Constructs and returns questions for cli to set up ec2 instance properties.

    Return:
        questions ([dicts]): a list of dictionaries with each dictionary representing
            a different question
    """

    amis = ['Amazon Linux AMI 2018.03.0:ami-0ec6517f6edbf8044']
    instance_types = ['t2.micro', 'p2.xlarge', 'g3s.xlarge', 'g3.4xlarge']
    sg_names = get_security_groups()
    
    questions = [
        {
            'type': 'list',
            'name': 'ami',
            'message': 'Select AMI',
            'choices': amis
        },
        {
            'type': 'list',
            'name': 'instance',
            'message': 'Select Instance Type',
            'choices': instance_types
        },
        {
            'type': 'checkbox',
            'name': 'sg',
            'message': 'Select all Security Groups',
            'choices': list_to_choices(sg_names)
        },
        {
            'type': 'input',
            'name': 'storage',
            'message': 'Enter storage amount (gb)'
        }
    ]

    return questions


def get_init_script():
    """
    Bash script represented as a string that will run on startup in the ec2 
    instance. Downloads the various requirements for raven and starts a docker 
    container with AWS credentials injected as environment variables.

    Return:
        user_data_script (string): The boto3 ec2 create instance method converts
            the string to a bash script
    """

    user_data_script = """
    #!/bin/bash
    sudo su
    yum -y update
    yum -y install docker
    service docker start
    docker pull ubuntu
    """

    aws_config = get_local_awsconfig()

    # adds AWS creds as environment variables to the docker container
    dock_string = "\ndocker run --name my_raven -d -it -e AWS_ACCESS_KEY_ID=%s -e AWS_SECRET_ACCESS_KEY=%s -e AWS_REGION=%s -e AWS_OUTPUT=%s ubuntu" %(aws_config['key_id'], aws_config['secret_key'], aws_config['region'], aws_config['output'])
    user_data_script += dock_string

    return user_data_script


def main():

    # style for pyinquirer
    style = style_from_dict({
    Token.Separator: '#cc5454',
    Token.QuestionMark: '#673ab7 bold',
    Token.Selected: '#cc5454',
    Token.Pointer: '#673ab7 bold',
    Token.Instruction: '',
    Token.Answer: '#f44336 bold',
    Token.Question: '',
    })

    print("Warning: choose these options carefully as they are associated with real costs")
    questions = get_questions()
    answers = prompt(questions, style=style)

    # prepare data for ec2
    storage_info=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {
                'VolumeSize': int(answers['storage']),
                'VolumeType': 'standard'
            }
        }
    ]
    user_name = 'ec2-user'
    bucket_name = 'tsl-ec2-keypair'
    user_data_script = get_init_script()
    security_groups = []
    for sg in answers['sg']:
        sg_id = sg.split(":")[0]
        security_groups.append(sg_id)

    ec2 = boto3.resource('ec2')
    s3 = boto3.resource('s3')
    
    # reads keypair from s3 bucket. If it doesn't exist, then creates both
    # the bucket and the keypair.

    bucket_exists = False
    for buck in list(s3.buckets.all()):
        if buck.name.startswith(bucket_name):
            bucket_name = buck.name
            bucket_exists = True

    rand_int = str(randint(1,9999999))
    rand_int = "0"*(7-len(rand_int)) + rand_int

    while not bucket_exists:
        try:
            print("creating bucket to store keypair...")
            bucket = s3.create_bucket(Bucket=bucket_name+'-'+rand_int, CreateBucketConfiguration={
            'LocationConstraint': 'us-west-1'})
            bucket_exists = True
            bucket_name = bucket_name+'-'+rand_int
        except:
            rand_int = str(randint(1,9999999))
            rand_int = "0"*(7-len(rand_int)) + rand_int

    bucket = s3.Bucket(bucket_name)

    file_exists = False
    for f in bucket.objects.all():
        if f.key == 'keypair.pem':
            file_exists = True

    if not file_exists:
        print("creating new keypair...")
        key_pair = ec2.create_key_pair(KeyName='keypair')
        key_pair_out = str(key_pair.key_material)

        s3.Object(bucket_name, 'keypair.pem').put(Body=bytes(key_pair_out, 'utf8'))

    temp_path = os.path.join(tempfile.gettempdir(), 'keypair.pem')
    # stores keypair for ssh access on local machine in tmp folder
    try:
        bucket.download_file('keypair.pem', temp_path)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    subprocess.call(['chmod', '400', temp_path])

    # creates ec2 instance
    instance = ec2.create_instances(
        ImageId=answers['ami'].split(":")[1],
        MinCount=1,
        MaxCount=1,
        InstanceType=answers['instance'],
        KeyName='keypair',
        BlockDeviceMappings=storage_info,
        SecurityGroupIds=security_groups,
        UserData=user_data_script
    )

    instance_id = [str(instance[0].id)]

    print("creating instance...")

    # waits until instance is properly initialized
    instance[0].wait_until_running()
    print("instance created\n")
    status = ec2.meta.client.describe_instance_status(InstanceIds=instance_id)
    idx = 0

    spinner = Spinner('initializing instance ')
    idx = 0
    while status['InstanceStatuses'][0]['InstanceStatus']['Status'] != 'ok':
        spinner.next()
        time.sleep(0.1)
        idx += 1
        if idx % 70 == 0:
            status = ec2.meta.client.describe_instance_status(InstanceIds=instance_id)
    print("\ninstance", instance_id[0], "initialized")


    # ssh into instance
    print("sshing into machine\n")
    instances = ec2.meta.client.describe_instances(InstanceIds=instance_id)
    dns = user_name + '@' + instances['Reservations'][0]['Instances'][0]['PublicDnsName']

    key_file = temp_path

    ssh_string = 'ssh -i ' + key_file + ' ' + dns

    print("\nSSH String: ", ssh_string)
    
    # automatically copies command to access bash of raven docker container
    command_str = "sudo docker exec -it my_raven bash"
    print("\nCommand to use raven docker container (copied to clipboard):", command_str,"\n\n")
    pyperclip.copy(command_str)

    subprocess.call(['ssh', '-i', key_file, dns])


if __name__ == "__main__":
    main()
