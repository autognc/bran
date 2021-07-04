"""
Filename:       bran.py
Author(s):      Nihal Dhamani
Contact:        nihaldhamani@gmail.com
Date Modified:  07/15/19

Bran is used as a cli to automatically create and ssh into an ec2 instance 
given user input settings. Bran automatically uploads files and configures the
environment to run ravenML trainings or Blender image generations. 
"""
import boto3
from botocore.exceptions import ClientError
import os
from bran.helpers.blender import get_blender_questions, get_blender_init_script
from bran.helpers.raven import get_raven_questions, get_raven_init_script, get_raven_cuda_version
from bran.helpers.utils import countdown, get_local_awsconfig
from random import randint
import subprocess
import time
from progress.spinner import Spinner
import pyperclip
from PyInquirer import style_from_dict, Token, prompt
from PyInquirer import Validator, ValidationError
from boto.s3.key import Key
import tempfile
from sys import platform


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

    purpose_question = [
        {
            'type': 'list',
            'name': 'purpose',
            'message': 'Select Instance Purpose',
            'choices': ['Blender Image Generation', 'RavenML Training', 'RavenML Dataset Creation']
        }
    ]
    purpose_answer = prompt(purpose_question, style=style)

    print("Warning: choose these options carefully as they are associated with real costs")
    if purpose_answer['purpose'] == 'Blender Image Generation':
        questions = get_blender_questions()
    else:
        if purpose_answer['purpose'] == 'RavenML Training':
            plugin_type = 'train'
        elif purpose_answer['purpose'] == 'RavenML Dataset Creation':
            plugin_type = 'dataset'
        questions = get_raven_questions(plugin_type)

    answers = prompt(questions, style=style)

    if len(answers['storage']) == 0:
        answers['storage'] = 100

    # prepare data for ec2
    if purpose_answer['purpose'] == 'Blender Image Generation':
        storage_info=[
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {
                    'VolumeSize': int(answers['storage']),
                    'VolumeType': 'gp2'
                }
            }
        ]
        user_name = 'ec2-user'
        user_data_script = get_blender_init_script(answers['script'].split('/')[-1])
    else:
        storage_info=[
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'VolumeSize': int(answers['storage']),
                    'VolumeType': 'gp2'
                }
            }
        ]
        user_name = 'ubuntu'
        cuda_version = get_raven_cuda_version(plugin_type, answers['branch'], answers['plugin'])
        user_data_script = get_raven_init_script(answers['plugin'], plugin_type, answers['gpu'], answers['branch'], cuda_version)
    
    bucket_name = 'tsl-ec2-keypair'
    security_groups = []
    for sg in answers['sg']:
        sg_id = sg.split(':')[0]
        security_groups.append(sg_id)

    ec2 = boto3.resource('ec2')
    s3 = boto3.resource('s3')
    
    # reads keypair from s3 bucket. If it doesn't exist, then creates both
    # the bucket and the keypair.

    aws_config = get_local_awsconfig()

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
            'LocationConstraint': aws_config['region']})
            bucket_exists = True
            bucket_name = bucket_name+'-'+rand_int
        except Exception as e:
            print("error creating bucket:", e)
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
        InstanceInitiatedShutdownBehavior='terminate',
        UserData=user_data_script
    )

    instance_id = [str(instance[0].id)]

    print("creating instance...")

    # waits until instance is properly initialized
    instance[0].wait_until_running()
    print("instance created\n")
    status = ec2.meta.client.describe_instance_status(InstanceIds=instance_id)
    spinner = Spinner('initializing instance ')
    
    idx = 0

    while status['InstanceStatuses'][0]['InstanceStatus']['Status'] != 'ok':
        spinner.next()
        time.sleep(0.1)
        idx += 1
        if idx % 70 == 0:
            status = ec2.meta.client.describe_instance_status(InstanceIds=instance_id)
    
    print("\ninstance", instance_id[0], "initialized")
    print("installing necessary software..")
    if purpose_answer["purpose"] == "RavenML Training":
        countdown(235) #for gpu the dependencies take a while to download
    else:
        time.sleep(5)


    # ssh into instance
    print("sshing into machine\n")
    instances = ec2.meta.client.describe_instances(InstanceIds=instance_id)
    dns = user_name + '@' + instances['Reservations'][0]['Instances'][0]['PublicDnsName']

    key_file = temp_path

    ssh_string = 'ssh -i ' + key_file + ' ' + dns

    if platform == "linux" or platform == "linux2":
        print("\nCommand to SSH", ssh_string,"\n\n")
    else:
        print("\nCommand to SSH (copied to clipboard):", ssh_string,"\n\n")
        pyperclip.copy(ssh_string)

    # scp relevant files to instance
    if purpose_answer["purpose"] == "Blender Image Generation":
        subprocess.call(['scp', '-i', key_file, answers["model"] ,dns + ":~"])
        subprocess.call(['scp', '-i', key_file, answers["script"] ,dns + ":~"])
        subprocess.call(['scp', '-i', key_file, answers["requirements"] ,dns + ":~"])
        subprocess.call(['ssh', '-i', key_file, dns, "pip3 install -r requirements.txt -t /home/ec2-user/.config/blender/2.82/scripts/addons/modules \n "])
        print("\n \n Command to generate images:  blender -b " + str(answers["model"].split("/")[-1] + " -P " + str(answers["script"].split("/")[-1] + " \n")))
    else:
        subprocess.call(['scp', '-i', key_file, answers["config"] ,dns + ":~"])
        if os.path.exists(os.path.expanduser('~/.ravenML/config.yml')):
            subprocess.call(['scp', '-i', key_file, os.path.join(os.path.expanduser('~/.ravenML'),'config.yml'),dns + ":~/.ravenML/config.yml"])
    
    subprocess.call(['ssh', '-i', key_file, dns])


if __name__ == "__main__":
    main()

