# Fetch_takehome

## Overview
The repo sets up a queue processor, which consumes incoming data from an AWS SQS queue hosted on localstack container and processes and ingests it to a POSTGRES DB. Find a video demo of the app here - [Demo](https://drive.google.com/file/d/1pxPzOQpuoLMQKhVgoA3Wi6GYpq4fPo5A/view?usp=sharing) 

## System Requirements
* Docker - [install](https://docs.docker.com/get-docker/)
* Python
* awscli-local installed using pip install awscli-local
* psql - [install](https://www.postgresql.org/download/)

Note - The app was built on a Windows machine

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

### Process data efficiently

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
### Mask PII data

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

### Connect to POSTGRES db

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
Note - Here when creating the engine for the DB connection, I have exposed the credentials required to connect to the DB. In an production ready system, this info would be passed to the application using a credential vault like AWS Secrets Manager

## App Build instructions

* Clone the git repository in your local system using the following command in the desired location
```
git clone git@github.com:arnavsinha109/Fetch_takehome.git
```
* Go inside the cloned repo to start building the containers. Find a video demo of the process here - [Demo](https://drive.google.com/file/d/1pxPzOQpuoLMQKhVgoA3Wi6GYpq4fPo5A/view?usp=sharing) 
* Build the docker containers using following command
```
docker-compose up --force-recreate
```
* The containers should be up and running now
* You can check the status of the queue by passing the following commands in another terminal instance. (Note- If the queue is not empty then it might show a message similar to the one given below, else it will return nothing)
 ```
 C:\Your\Path> docker exec -it localstack bash
 root@95a0f9596a7e:/opt/code/localstack# awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/login-queue
 {
     "Messages": [
         {
             "MessageId": "d6507b56-5e60-4023-93c5-c5a4dc954fb2",
             "ReceiptHandle": "MThiNWI2NTItNmRhZS00MjRjLTljOGMtN2UwMmNhMjQwMDI1IGFybjphd3M6c3FzOnVzLWVhc3QtMTowMDAwMDAwMDAwMDA6bG9naW4tcXVldWUgZDY1MDdiNTYtNWU2MC00MDIzLTkzYzUtYzVhNGRjOTU0ZmIyIDE2Nzg4MjUxNDUuMTc5OTQyNA==",
             "MD5OfBody": "e4f1de8c099c0acd7cb05ba9e790ac02",
             "Body": "{\"user_id\": \"424cdd21-063a-43a7-b91b-7ca1a833afae\", \"app_version\": \"2.3.0\", \"device_type\": \"android\", \"ip\": \"199.172.111.135\", \"locale\": \"RU\", \"device_id\": \"593-47-5928\"}"
         }
     ]
 }
 root@95a0f9596a7e:/opt/code/localstack#
 ```
* You can check the status of your db container by passing the following commands in another terminal instance (Note- if the queue processor is not running, then the table should be empty, else it should show some data)
 ```
 C:\Your\Path> docker exec -it postgres bash
 root@c268d83cb716:/# psql -d postgres -U postgres -p 5432 -h localhost -W
 Password for user postgres:
 psql (10.21 (Debian 10.21-1.pgdg90+1))
 Type "help" for help.

 postgres=# select * from user_logins;
  user_id | device_type | masked_ip | masked_device_id | locale | app_version | create_date
 ---------+-------------+-----------+------------------+--------+-------------+-------------
 (0 rows)

 postgres=# select * from user_logins;
                user_id                | device_type |                            masked_ip                             |
                  masked_device_id                         | locale | app_version | create_date
 --------------------------------------+-------------+------------------------------------------------------------------+------------------------------------------------------------------+--------+-------------+-------------
  c0173198-76a8-4e67-bfc2-74eaa3bbff57 | ios         | 7b03f7d723535706b4777384fc906d18a4376bb84cebb50dc22c6eb9bddf00cb | a857e702f98990716938a0d74c3dc2dc565e4448833e2cf91c6ab26fc0e9971f | PH     |          26 | 2023-03-14
  66e0635b-ce36-4ec7-aa9e-8a8fca9b83d4 | ios         | fa7fca28c658d75a751b60e262602e1b11f4149274af6ec0d8c82a8619a51437 | e84fb3e15175d0a2492de6c02a99595c1343db7321ad6bb5f62052edd00a84f8 |        |         221 | 2023-03-14
  181452ad-20c3-4e93-86ad-1934c9248903 | android     | b21d1c922d9e9d1b913ade3265baa7fc43c757976dcd7cac3ed2043176655396 | 94b571f680b8f41547047f24e385334265773d33ab643bfc6f1684e21b8b34d9 | ID     |          96 | 2023-03-14
  60b9441c-e39d-406f-bba0-c7ff0e0ee07f | android     | 587f5a111a1f2adb462f778574a91b93de3b29889deca6e25dd363588a5e0ccb | 3102ec6d1310b3db007305eaa5802b3831d4b4ae5f165e21ee1e3298f55e5616 | FR     |          46 | 2023-03-14
 ```
## Additional thoughts and comments on Deployment and Production Readiness Strategies
* One possible deployment strategy for this application it to deploy the container app on AWS Fargate clusters using AWS ECS (Elastic Container Service)
    * The app would perform the same basic functions with more finesse
    * Other Components to be added -
        * More queue worker instances for faster processing
        * Dead Letter Queues to store messages that were dequeued multiple times but could not be processed successfully to stop them from blocking the queue
        * Implementing a credential vault (like AWS Secret Manager) to secure the different components of the system
        * Heath check capabilities
            * Monitoring
            * Logging
            * CloudWatch Dashboards
            * Alert system to generate alert in case some service goes down
* We could use queue based scaling as a scale out strategy
   * In case the size of the queue increases because of increase in dataflow, we can configure the Fargate app to scale out to handle the increase in data
* PII data handling could be done by storing it in secure database or with a designated third party service provider in accordance with the local data privacy protection laws
   * For instance, the data could be stored locally for regions with GDPR like data privacy and security laws
   * Additionally, we might also need to provide users capability to decide the fate of their data by allowing them to delete it if required by the law
* Assumptions made in the current implementation
   * Data in queue without necessary fields is considered rogue and deleted without being ingested in the DB
   * App version data when stored in the DB in processed as an integer after replacing the '.' characters in its value in the message to keep up with the DB constrains
   * In case, the message does not have a viable value for 'ip' or 'device_id', a blank is encrypted using the SHA256 hashing scheme and their masked values will repeat across users with unknown/blank values for these fields 
