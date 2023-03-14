# Fetch_takehome

## Overview
The repo sets up a queue processor, which consumes incoming data from an AWS SQS queue hosted on localstack container and processes and ingests it to a POSTGRES DB

## System Requirements
* Docker - [install](https://docs.docker.com/get-docker/)
* Python
* awscli-local installed using pip install awscli-local
* psql - [install](https://www.postgresql.org/download/)

## Functional Requirements and their implementations
### Reading Messages in Queue
This is achieved by using AWS SDK 'boto3' in Python

```
import boto3

queue_url = "http://localstack:4566/000000000000/login-queue"

sqs = boto3.client("sqs", endpoint_url="http://localstack:4566/_aws/sqs/", region_name='us-east-1')

response = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=20)
```

Note - Set AWS default_region to 'us-east-1' and pass dummy AWS credentials - AWS_ACCESS_KEY_ID='123', AWS_SECRET_ACCESS_KEY='xyz' as environment variables for your application in docker-compose.yaml file to avoid boto3 errors even when working with localstack

## Process data efficiently

Achieved by parsing the message received as JSON and processed to handle anomalies before being ingested in the DB in the following steps-
* Parse message['Body'] as JSON
* Perform sanity check on the JSON and see if all expected keys are present
* If JSON passes sanity check
  * encrypt PII data
  * ingest data in DB
* Else delete message because of its rogue nature 

```
def process_messages(message):
    msg_json = json.loads(message["Body"])

    try:
        validate_message(message=msg_json)
    except:
        delete_rogue_message(message)

    msg_json["masked_ip"] = create_hash(msg_json.get("ip", ""))
    msg_json["masked_device_id"] = create_hash(msg_json.get("device_id", ""))
    msg_json.pop("ip")
    msg_json.pop("device_id")
    msg_json["app_version"] = int(msg_json["app_version"].replace(".", ""))

    print(msg_json)

    # ingest data in the user_logins table
    add_user_info(msg_json)
```
## Mask PII data

Achieved by using SHA256 hashing in the create_hash() function on the msg_json["ip"] and msg_json["device_id"] after the message JSON passes sanity check
We retain only the first 256 characters of the hash generated to stay within the attribute constraints of "masked_ip" and "masked_device_id" fields in the DB

```
def create_hash(string):
    # Create a SHA256 hash object
    hash_object = hashlib.sha256()

    # Update the hash object with the string
    hash_object.update(string.encode("utf-8"))

    # Get the hexadecimal representation of the hash
    hash_hex = hash_object.hexdigest()[:256]

    return hash_hex
```

## Connect to POSTGRES db

After the message passes sanity check. We are ready to ingest the user login data in the POSTGRES db. We do that using SQLAlchemy ORM available in Python.

```
from sqlalchemy import create_engine, Column, String, Integer, Date

from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import sessionmaker
import psycopg2

# create engine
engine = create_engine("postgresql://postgres:postgres@postgres:5432/postgres")

# create base class
Base = declarative_base()


# define UserLogin class
class UserLogins(Base):
    __tablename__ = "user_logins"

    user_id = Column(String(128), primary_key=True)
    device_type = Column(String(32), nullable=False)
    masked_ip = Column(String(256), nullable=False)
    masked_device_id = Column(String(256), nullable=False)
    locale = Column(String(32), nullable=False)
    app_version = Column(Integer, nullable=False)
    create_date = Column(Date, nullable=False)

    def __repr__(self):
        return f"<UserLogin(user_id='{self.user_id}', device_type='{self.device_type}', masked_ip='{self.masked_ip}', masked_device_id='{self.masked_device_id}', locale='{self.locale}', app_version={self.app_version}, create_date='{self.create_date}')>"


# create sessionmaker
Session = sessionmaker(bind=engine)


def add_user_info(user_data):
    # create session
    session = Session()

    # define dictionary with column values for new row
    user_data.update({"create_date": datetime.now()})

    # create new UserLogin object from dictionary
    new_user_login = UserLogins(**user_data)

    # add new UserLogin object to session
    session.add(new_user_login)

    # commit transaction
    session.commit()

    # close session
    session.close()
```
