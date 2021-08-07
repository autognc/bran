import boto3
import os
import configparser
from os.path import expanduser
import time

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
    for key in config:
        aws_config[key]['key_id'] = config['default']['aws_access_key_id']
        aws_config[key]['secret_key'] = config['default']['aws_secret_access_key']
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
    l = sorted(l)
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


def get_comet_api_key():

    ssm = boto3.client('ssm')
    
    key_parameter = ssm.get_parameter(Name='COMET_API_KEY', WithDecryption=True)
    api_key = key_parameter['Parameter']['Value']

    return api_key

def countdown(t):
    """
        sleeps for t seconds and displays a nice little countdown timer during that time
        
        Args:
            t (int): time to sleep for
    """
    while t:
        mins, secs = divmod(t, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        print(timeformat, end='\r')
        time.sleep(1)
        t -= 1
