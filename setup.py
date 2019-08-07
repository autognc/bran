from setuptools import setup

setup(
    name='bran',
    version='1.1.0',
    description='EC2 instance creation CLI',
    packages=['bran'],
    install_requires=[
        'boto3>=1.9.104',
        'botocore>=1.12.104',
        'boto>=2.49.0',
        'pyinquirer>=1.0.3',
        'pyperclip>=1.7.0',
        'progress>=1.4'
    ],
    entry_points='''
      [console_scripts]
      bran=bran.bran:main
    ''',
)
