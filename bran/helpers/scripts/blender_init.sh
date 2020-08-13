#!/bin/bash
echo "export EC2_ID=$(echo $(curl http://169.254.169.254/latest/meta-data/instance-id))" >> /etc/profile
echo "export AWS_ACCESS_KEY_ID=$(echo <key_id>)" >> /etc/profile
echo "export AWS_SECRET_ACCESS_KEY=$(echo <secret_id>)" >> /etc/profile
echo "export AWS_DEFAULT_REGION=$(echo <aws_region>)" >> /etc/profile
source /etc/profile
pip3 install git+https://github.com/autognc/starfish --no-deps -t /home/ec2-user/.config/blender/2.82/scripts/addons/modules
pip3 install opencv-python==4.2.0.32 -t /home/ec2-user/.config/blender/2.82/scripts/addons/modules
cd /home/ec2-user
sudo yum install -y libXext libSM libXrender
n=0
procnum=`ps -aux | grep <script_name>| grep -v grep | grep -v Tl`
while [ $n == 0 ] || [[ $procnum != "" ]] 
do
if [[ $procnum != "" ]]
then
n=$n+1
fi
sleep 20m
procnum=`ps -aux | grep <script_name>| grep -v grep | grep -v Tl`
done
sleep 20m
sudo shutdown -P now
