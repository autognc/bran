from bran.helpers.utils import get_security_groups, get_local_awsconfig, list_to_choices
import os

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
    source /etc/profile
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
