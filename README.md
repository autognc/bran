# Bran

Bran is used as a cli to automatically create and ssh into an ec2 instance given user input settings. 
Bran automatically sets up the docker container needed to run raven.

# Requirements

The AWSCLI must be installed and configured with ```aws configure``` before running Bran.

Developed on Python 3.6.8

# Instructions to Run
1. Make sure that the credentials are stored at ```~/.aws/credentials```
2. Command to run: python bran.py
3. Select options for ec2 instance parameters
4. Wait until initialized
5. Enter ```yes``` if prompted about adding ssh key to your repo
6. You should be ssh'd into the instance already
7. The command to run the raven container bash is copied to the clipboard