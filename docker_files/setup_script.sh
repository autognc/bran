#!/bin/bash
set -e

apt-get update
apt-get -y install git
git clone https://github.com/autognc/ravenML.git
#apt-get -y install python3.6
apt-get -y install python3-pip
update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1
#echo "alias python=python3" >> ~/.bashrc
#echo "alias pip=pip3" >> ~/.bashrc
#source ~/.bashrc
pip install --upgrade setuptools
cd ravenML
git checkout bbox_plugin_dev
pip install -r requirements.txt
pip install -e .
pip install halo
pip install pyyaml
cd plugins
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
./install_all.sh -c