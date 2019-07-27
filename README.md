# Bran

Bran is used as a cli to automatically create and ssh into an ec2 instance given user input settings. 
Bran automatically sets up the docker container needed to run raven.

## Requirements

The AWSCLI must be installed and configured with ```aws configure``` before running Bran.

Developed on Python 3.6.8

## Installation

1. Clone repository onto local machine: ```git clone https://github.com/autognc/bran.git```
2. Navigate to the downloaded repository: ```cd bran```
3. Install with pip: ```pip install -e .```

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
3. Select options for ec2 instance parameters. **Use gs3.4xlarge for GPU trainings and t2.medium for CPU trainings.** Make sure to select the custom security group created earlier.
4. Wait until initialized
5. Enter ```yes``` if prompted about adding ssh key to your repo and click enter
6. You should be ssh'd into the instance automatically with ravenML installed with the plugin selected