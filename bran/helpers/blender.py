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
    script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts', 'blender_init.sh')
    
    with open(script_path, 'r') as stream:
        script = stream.read()
    
    script = script.replace('<key_id>', aws_config['key_id'] )
    script = script.replace('<secret_id>', aws_config['secret_key'] )
    script = script.replace('<aws_region>', aws_config['region'])
    script = script.replace('<script_name>', script_name)

    return script
