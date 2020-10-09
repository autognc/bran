from bran.helpers.utils import get_security_groups, get_local_awsconfig, list_to_choices, get_comet_api_key
import git
import os
import requests

def get_raven_branches(url="https://github.com/autognc/ravenML-train-plugins"):
    """
    
        Returns a list of branch names at github repo specified by url.
        
        Args:
            url (str): url to check for branch names. defaults to "https://github.com/autognc/ravenML-train-plugins"
        Return:
            remote_refs (list): list of ravenML-train-plugins branch names
    """

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
    # TODO: add AMI's, check CUDA versions, add support for comet-opt plugin, add lab computer
    amis = ['Ubuntu Deep Learning:ami-0cc472544ce594a19']
    instance_types = ['t2.large', 'g4dn.xlarge','g3.4xlarge', 't2.medium','t2.micro']
    sg_names = get_security_groups()
    branches = get_raven_branches()
    plugins = ['rmltraintfbbox', 'rmltraintfbboxcometopt','rmltraintfbboxlegacy','rmltraintfinstance', 'rmltraintfposeregression', 'rmltraintfsemantic']
    
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

def get_raven_init_script(plugin, gpu, branch, cuda_version='10.0'):
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
    
    script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts', 'raven_init.sh')
    
    with open(script_path, 'r') as stream:
        script = stream.read()
    script = script.replace('<key_id>', aws_config['key_id'] )
    script = script.replace('<secret_id>', aws_config['secret_key'] )
    script = script.replace('<aws_region>', aws_config['region'])
    script = script.replace('<comet_key>', comet_api_key)
    script = script.replace('<gpu_var>', gpu)
    script = script.replace('<branch_name>', branch)
    script = script.replace('<plugin_name>', plugin)
    script = script.replace('<cuda_version>', cuda_version)
    return script

def get_raven_cuda_version(branch, plugin):
    """
        Gets the setup.py of the ravenML-train-plugins branch/plugin from the github website 
        and returns the correct cuda version to use the tensorflow version listed in the setup.py
        
        Args:
            branch (str)-- branch of ravenML-train-plugins at https://github.com/autognc/ravenML-train-plugins
            plugin (str)-- ravenML train plugin being setup by bran
        Returns:
            cuda version (str)-- '10.1' if tf2 is required. '10.0' otherwise. 
                This is used to create symlink in userdata script.(see ./scripts/raven_init.sh)
    """
    url = "https://github.com/autognc/ravenML-train-plugins/blob/{}/{}/setup.py".format(branch, plugin)
    
    req = requests.get(url)
    
    content = str(req.content)
    
    loc = content.find('tensorflow==')
    
    version = int(content[loc+len('tensorflow==')])
    
    if version == 2:
        return '10.1'
    else:
        return '10.0'
    
    
    
    
    
    
    
    
