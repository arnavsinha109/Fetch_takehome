# Fetch_takehome

## Overview
The repo sets up a queue processor, which consumes incoming data from an AWS SQS queue hosted on localstack container and processes and ingests it to a POSTGRES DB

## System Requirements
* Docker - [install](https://docs.docker.com/get-docker/)
* Python
* awscli-local installed using pip install awscli-local
* psql - [install](https://www.postgresql.org/download/)

## Functional Requirements
### Reading Messages in Queue
This is achieved by using AWS SDK 'boto3' in Python
'''
queue_url = "http://localstack:4566/000000000000/login-queue"

sqs = boto3.client("sqs", endpoint_url="http://localstack:4566/_aws/sqs/", region_name='us-east-1')

response = sqs.receive_message(
    QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=20
)
'''
