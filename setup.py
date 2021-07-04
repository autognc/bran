from setuptools import setup, find_packages

setup(
    name='bran',
    version='1.1.1',
    description='EC2 instance creation CLI',
    packages=find_packages(),
    install_requires=[
        'boto3>=1.9.104',
        'botocore>=1.12.104',
        'boto>=2.49.0',
        'pyinquirer>=1.0.3',
        'pyperclip>=1.7.0',
        'progress>=1.4',
        'gitpython>=3.0.0',
        'requests'
    ],
    entry_points='''
      [console_scripts]
      bran=bran.bran:main
    ''',
)
