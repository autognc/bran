#!/bin/bash
set -e

apt-get update
apt-get -y install git
git clone https://github.com/autognc/ravenML.git
#apt-get -y install python3.6
apt-get -y install python3-pip
echo "alias python=python3" >> ~/.bashrc
echo "alias pip=pip3" >> ~/.bashrc
source ~/.bashrc
pip3 install --upgrade setuptools
cd ravenML
git checkout bbox_plugin_dev
pip3 install -r requirements.txt
pip3 install -e .


exec "$@"
