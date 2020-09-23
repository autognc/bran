# Bran

Bran is used as a cli to automatically create and ssh into an ec2 instance given user input settings. 
Bran automatically sets up the docker container needed to run raven.

## Requirements

The AWSCLI must be installed and configured with ```aws configure``` before running Bran.

Developed on Python 3.6.8

## Installation

1. Clone repository onto local machine: ```git clone https://github.com/autognc/bran.git```
2. Navigate to the downloaded repository: ```cd bran```
3. Create conda environment: ```conda env create -f environment.yml```
4. Activate conda environment: ```conda activate bran```
5. Install with pip: ```pip install -e .```

## Configure Security Groups

1. Go to the EC2 Dashboard in the AWS Console
2. Click **Security Groups** under Network & Security located in the left column
3. Make sure you are in the same region on the top right as your local aws configuration
4. Click **Create Security Group** 
5. Enter a **Security Group Name** and **Description**
6. With the **Inbound** field highlighted, click **Add Rule**
7. Select **Custom TCP** for Type
8. Enter **22** for **Port Range**
9. Choose **Anywhere** for **Source**
10. Enter a **Description** for the security group
11. Click **Create**

## Instructions to Run
1. Make sure that the credentials are stored at ```~/.aws/credentials```
2. Command to run: ```bran```
3. Choose between Blender image generation and ravenML training
  * For ravenML: 
    1. Choose plugin to install and ravenML-train-plugins branch to install from
    2. Specify path to ravenML config file
  * For Blender: 
    1. Specify path to .blend file
    2. Specify path to image generation script
    3. Specify path to requirements.txt(listing of python modules needed to run image generation script)
4. Select options for ec2 instance parameters. **Use g3.4xlarge for GPU trainings and t2.medium for CPU trainings.** Make sure to select the custom security group created earlier. Use around 120 gbs for storage or 160 gbs if using an especially large dataset.
5. Wait until initialized
7. Enter ```yes``` if prompted about adding ssh key to your repo and click enter
8. You should be ssh'd into the instance automatically with ravenML installed with the plugin selected
9. start tmux by typing `tmux` into the shell
10. type the ravenML training or Blender image generation command you want inside the started tmux session
11. leave/detach the tmux session by typing `Ctrl+b` and then `d`
