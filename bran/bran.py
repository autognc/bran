"""
Filename:       bran.py
Author(s):      Nihal Dhamani
Contact:        nihaldhamani@gmail.com
Date Modified:  07/15/19

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
from sys import platform
import git

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

def get_raven_branches():
    """
        Returns a list of branch names in ravenML-training-plugins
        
        Return:
            remote_refs (list): list of ravenML-training-plugins branch names
    """
    url = "https://github.com/autognc/ravenML-train-plugins"
    remote_refs = []
    g = git.cmd.Git()
    for ref in g.ls_remote(url).split('\n'):
        ref = ref.split('\t')[1]
        if ref.startswith("refs/heads/"):
            remote_refs.append(ref[11:])
    return remote_refs
    
def get_raven_questions():
    """
    Constructs and returns questions for cli to set up ec2 instance properties for a RavenML training.

    Return:
        questions ([dicts]): a list of dictionaries with each dictionary representing
            a different question
    """
    # TODO: add AMI's, check CUDA versions, add support for comet-opt plugin
    amis = ['Ubuntu Deep Learning:ami-0f4ae762b012dbf78','Ubuntu Deep Learning:ami-06f57f0480ec007e3']
    instance_types = ['t2.large', 'g4dn.xlarge','g3.4xlarge', 't2.medium','t2.micro']
    sg_names = get_security_groups()
    branches = get_raven_branches()
    plugins = ['rmltraintfbbox', 'rmltraintfinstance', 'rmltraintfposeregression', 'rmltraintfsemantic']
    
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
        },
        {
            'type': 'list',
            'name': 'plugin',
            'message': 'Select the ravenML plugin you wish to install',
            'choices': list_to_choices(plugins)
        },
        {
            'type': 'list',
            'name': 'branch',
            'message': 'Select the ravenML-train-plugins branch you wish to clone',
            'choices': list_to_choices(branches)
        },
        {
            'type': 'input',
            'name': 'config',
            'message': 'Enter filepath of ravenML config file',
            'validate': lambda p: os.path.isfile(p)
        },
        {
            'type': 'list',
            'name': 'gpu',
            'message': 'Train on GPU or CPU?',
            'choices': list_to_choices(['GPU', 'CPU'])
        }
    ]

    return questions

def get_blender_questions():
    """
    Constructs and returns questions for cli to set up ec2 instance properties for image generation with Blender.

    Return:
        questions ([dicts]): a list of dictionaries with each dictionary representing
            a different question
    """

    amis = ['Blender:ami-0c66a2d9734c3f1aa', "Blender-GPU:ami-0e96d01a5638bccd8"]
    instance_types = ['t2.large', 'g4dn.xlarge','g3.4xlarge', 't2.medium','t2.micro']
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
        },
        {
            'type': 'input',
            'name': 'model',
            'message': 'Enter filepath of desired blender model',
            'validate': lambda p: os.path.isfile(p)
        },
        {
            'type': 'input',
            'name': 'script',
            'message': 'Enter filepath of generation script',
            'validate': lambda p: os.path.isfile(p)
        },
        {
            'type': 'input',
            'name': 'requirements',
            'message': 'Enter filepath of requirements.txt file',
            'validate': lambda t: os.path.isfile(t) 
        }
    ]
    return questions


def get_raven_init_script(plugin, gpu, branch):
    """
    Bash script represented as a string that will run on startup in the ec2 
    instance. Downloads the various requirements for raven and starts a docker 
    container with AWS credentials injected as environment variables.

    Return:
        user_data_script (string): The boto3 ec2 create instance method converts
            the string to a bash script
    """
    aws_config = get_local_awsconfig()
    comet_api_key = get_comet_api_key()
   
    ## the following commands are potentially useful but are not needed atm. saving for future use
    # pip install "git+https://github.com/autognc/ravenML-train-plugins.git#egg=rmltraintfbbox&subdirectory=rmltraintfbbox" - pip install from subdirectory of github repo
    # source /home/ubuntu/anaconda3/bin/activate /home/ubuntu/anaconda3/envs/ravenml - enter conda env that belongs to a different user
    
    # this script runs config for ravenML upon startup some things to note:
    # ubuntu deep learning AMIs run the user data script as the root user, however aws makes you connect as ubuntu
    # therefore, one should use chown -R ubuntu:ubuntu <filepath> on any file/directory that is created in ths script 
    # aws docs say not to use sudo as a prefix to any command in this script
    user_data_script = """#!/bin/bash
    # direct stdout to /var/log/user-data.log
    exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
    
    # set environment variables
    echo "export EC2_ID=$(echo $(curl http://169.254.169.254/latest/meta-data/instance-id))" >> /etc/profile
    echo "export AWS_ACCESS_KEY_ID=$(echo {})" >> /etc/profile
    echo "export AWS_SECRET_ACCESS_KEY=$(echo {})" >> /etc/profile
    echo "export AWS_DEFAULT_REGION=$(echo {})" >> /etc/profile
    echo "export COMET_API_KEY=$(echo {})" >> /etc/profile
    echo "export RML_{}=true" >> /etc/profile
    source /etc/profile
    
    # give ubuntu root permissions. TODO: is this dangerous?
    echo "ubuntu ALL = NOPASSWD: ALL" >> /etc/sudoers
    source /etc/sudoers
    
    # enable conda command
    echo ". /home/ubuntu/anaconda3/etc/profile.d/conda.sh" >> /home/ubuntu/.bashrc
    cd /home/ubuntu
    source .bashrc
    
    #clone repos and create conda env
    git clone https://github.com/autognc/ravenML.git
    cd /home/ubuntu/ravenML/
    source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
    conda env create -f environment.yml
    source /home/ubuntu/anaconda3/bin/activate /home/ubuntu/anaconda3/envs/ravenml
    cd /home/ubuntu
    
    # TODO:
    # would be better to pip install directly from github instead of cloning, but data_files keyword in setup.py of rmltraintfbbox
    # causes install to fail. According to setuptools docs, data_files is deprecated and does not work with wheels. 
    # Need to look into removing that from all branches
    git clone --single-branch -b {} https://github.com/autognc/ravenML-train-plugins
    
    # install rml and plugin, set permissions so ubuntu user can pip install to ravenml conda env
    cd /home/ubuntu/ravenML/
    pip install -v -e . 
    chown -R ubuntu:ubuntu /home/ubuntu/anaconda3/envs/ravenml
    chown -R ubuntu:ubuntu /home/ubuntu/ravenML-train-plugins/
    chown -R ubuntu:ubuntu /home/ubuntu/ravenML/
    
    # for some reason object detection protos are installed incorrectly  if the root user installs using 'pip install -e .'
    # instead we run the install command as ubuntu and that seems to work
    su - ubuntu -c "/home/ubuntu/anaconda3/envs/ravenml/bin/pip install -e /home/ubuntu/ravenML-train-plugins/{}/"
    
    # set permissions again to account for any new files created during install
    cd /home/ubuntu
    chown -R ubuntu:ubuntu /home/ubuntu/anaconda3/envs/ravenml
    chown -R ubuntu:ubuntu /home/ubuntu/ravenML-train-plugins/
    chown -R ubuntu:ubuntu /home/ubuntu/ravenML/
    """.format(aws_config['key_id'], aws_config['secret_key'], aws_config['region'], comet_api_key, gpu, branch, plugin)

    return user_data_script


def get_blender_init_script(script_name):
    """
    Bash script represented as a string that will run on startup in the ec2 
    instance. Adds Blender directory to path. Periodically checks if blender
    script has finished and kills the intance once the script has stopped

    Return:
        user_data_script (string): The boto3 ec2 create instance method converts
            the string to a bash script
    """

    aws_config = get_local_awsconfig()

    user_data_script = """#!/bin/bash
    echo "export EC2_ID=$(echo $(curl http://169.254.169.254/latest/meta-data/instance-id))" >> /etc/profile
    echo "export AWS_ACCESS_KEY_ID=$(echo {})" >> /etc/profile
    echo "export AWS_SECRET_ACCESS_KEY=$(echo {})" >> /etc/profile
    echo "export AWS_DEFAULT_REGION=$(echo {})" >> /etc/profile
    pip3 install git+https://github.com/autognc/starfish --no-deps -t /home/ec2-user/.config/blender/2.82/scripts/addons/modules
    pip3 install opencv-python -t /home/ec2-user/.config/blender/2.82/scripts/addons/modules
    cd /home/ec2-user
    sudo yum install -y libXext libSM libXrender
    n=0
    procnum=`ps -aux | grep {}| grep -v grep | grep -v Tl`
    while [ $n == 0 ] || [[ $procnum != "" ]] 
    do
    if [[ $procnum != "" ]]
    then
    n=$n+1
    fi
    sleep 20m
    procnum=`ps -aux | grep {}| grep -v grep | grep -v Tl`
    done
    sleep 20m
    sudo shutdown -P now
    """.format(aws_config['key_id'], aws_config['secret_key'], aws_config['region'], script_name, script_name)

    return user_data_script

def get_comet_api_key():

    ssm = boto3.client('ssm')
    
    key_parameter = ssm.get_parameter(Name='COMET_API_KEY', WithDecryption=True)
    api_key = key_parameter['Parameter']['Value']

    return api_key

def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        print(timeformat, end='\r')
        time.sleep(1)
        t -= 1

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
            'choices': ["Blender Image Generation", "RavenML Training"]
        }
    ]
    purpose_answer = prompt(purpose_question, style=style)

    print("Warning: choose these options carefully as they are associated with real costs")
    if purpose_answer["purpose"] == "RavenML Training":
        questions = get_raven_questions()
    else:
        questions = get_blender_questions()
    answers = prompt(questions, style=style)

    if len(answers['storage']) == 0:
        answers['storage'] = 100

    # prepare data for ec2

    if purpose_answer["purpose"] == "RavenML Training":
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
        user_data_script = get_raven_init_script(answers['plugin'], answers['gpu'], answers['branch'])
    else:
        storage_info=[
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {
                    'VolumeSize': int(answers['storage']),
                    'VolumeType': 'gp2'
                }
            }
        ]
        user_name = "ec2-user"
        user_data_script = get_blender_init_script(answers['script'].split('/')[-1])

    bucket_name = 'tsl-ec2-keypair'
    security_groups = []
    for sg in answers['sg']:
        sg_id = sg.split(":")[0]
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
    
    subprocess.call(['ssh', '-i', key_file, dns])


if __name__ == "__main__":
    main()

