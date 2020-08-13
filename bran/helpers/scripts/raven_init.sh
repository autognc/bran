#!/bin/bash
# the following commands are potentially useful but are not needed/do not work atm. saving for future use
# pip install "git+https://github.com/autognc/ravenML-train-plugins.git#egg=rmltraintfbbox&subdirectory=rmltraintfbbox" - pip install from subdirectory of github repo
# source /home/ubuntu/anaconda3/bin/activate /home/ubuntu/anaconda3/envs/ravenml - enter conda env that belongs to a different user

# this script runs config for ravenML upon startup some things to note:
# ubuntu deep learning AMIs run the user data script as the root user, however aws makes you connect as ubuntu
# therefore, one should use chown -R ubuntu:ubuntu <filepath> on any file/directory that is created in this script 
# aws docs say not to use sudo as a prefix to any command in this script

# direct stdout to /var/log/user-data.log
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# set environment variables
echo "export EC2_ID=$(echo $(curl http://169.254.169.254/latest/meta-data/instance-id))" >> /etc/profile
echo "export AWS_ACCESS_KEY_ID=$(echo <key_id>)" >> /etc/profile
echo "export AWS_SECRET_ACCESS_KEY=$(echo <secret_id>)" >> /etc/profile
echo "export AWS_DEFAULT_REGION=$(echo <aws_region>)" >> /etc/profile
echo "export COMET_API_KEY=$(echo <comet_key>)" >> /etc/profile
echo "export RML_<gpu_var>=true" >> /etc/profile
source /etc/profile

# give ubuntu root permissions.
echo "ubuntu ALL = NOPASSWD: ALL" >> /etc/sudoers
source /etc/sudoers

# enable conda command
echo ". /home/ubuntu/anaconda3/etc/profile.d/conda.sh" >> /home/ubuntu/.bashrc
cd /home/ubuntu
source .bashrc

mkdir /home/ubuntu/.ravenML
chown -R ubuntu:ubuntu /home/ubuntu/.ravenML/

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
git clone --single-branch -b <branch_name> https://github.com/autognc/ravenML-train-plugins

# install rml and plugin, set permissions so ubuntu user can pip install to ravenml conda env
cd /home/ubuntu/ravenML/
pip install -v -e . 
chown -R ubuntu:ubuntu /home/ubuntu/anaconda3/envs/ravenml
chown -R ubuntu:ubuntu /home/ubuntu/ravenML-train-plugins/
chown -R ubuntu:ubuntu /home/ubuntu/ravenML/

# for some reason object detection protos are installed incorrectly  if the root user installs using 'pip install -e .'
# instead we run the install command as ubuntu and that seems to work
su - ubuntu -c "/home/ubuntu/anaconda3/envs/ravenml/bin/pip install -e /home/ubuntu/ravenML-train-plugins/<plugin_name>/"

# set permissions again to account for any new files created during install
cd /home/ubuntu
chown -R ubuntu:ubuntu /home/ubuntu/anaconda3/envs/ravenml
chown -R ubuntu:ubuntu /home/ubuntu/ravenML-train-plugins/
chown -R ubuntu:ubuntu /home/ubuntu/ravenML/

## set cuda symlink to cuda 10.0 for tf1 or 10.1 for tf2
cd /usr/local
rm cuda
ln -s cuda-<cuda_version> cuda
