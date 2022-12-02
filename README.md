# simple-py-rss-to-mastodon

## Description

This code is an adaptation of a python-based script that currently pulls a few RSS feeds into the `theatl.social` Mastodon site which I presently operate.

There is, of course, many opportunities for improvement and extensibility. As time and resources permit, this script will be updated in kind.

__This code is intended as a demonstration. A deployable version of this code will be developed in the near future.__

## Installation 

### Prerequisites

1. Python 3.x
2. [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. A DynamoDB Table pre-created on AWS, whose name and region should be manually input into your template.yml
4. Docker (to build Lambda container for deployment)
5. AWS Credentials for utilizing the SAM CLI
   1. could be located in `$HOME/.aws`

### Important Note

- Please review the comments in `python/app.py` regarding creation of the client application token and secret for Mastodon

### TODO:

1. Update AWS Template to include creation of DynamoDB
2. Add alternative to using AWS
3. Add additional code to manage storage of Mastodon application credentials
4. Unit testing

### Commands

`make build`: Builds the files to be uploaded to lambda, reading the `template.yml` file

`make deploy`: Deploys the files to be uploaded to lambda in guided mode, creating a `config.toml` file.