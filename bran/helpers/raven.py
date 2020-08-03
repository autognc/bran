from bran.helpers.utils import get_security_groups, get_local_awsconfig, list_to_choices, get_comet_api_key
import git
import os


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

