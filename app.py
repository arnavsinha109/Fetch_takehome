import boto3
import sys
import argparse
import json
import socket
import traceback
import time
import os
import hashlib
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


def create_hash(string):
    # Create a SHA256 hash object
    hash_object = hashlib.sha256()

    # Update the hash object with the string
    hash_object.update(string.encode("utf-8"))

    # Get the hexadecimal representation of the hash
    hash_hex = hash_object.hexdigest()[:256]

    return hash_hex


def validate_message(message):
    # Verify that the message contains all the expected keys

    expected_keys = {'user_id', 'device_type', 'ip', 'device_id', 'locale', 'app_version'}
    if not expected_keys.issubset(set(message.keys())):
        raise ValueError('Missing keys in message')


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

def delete_rogue_message(message):
    queue_url = "http://localstack:4566/000000000000/login-queue"

    sqs = boto3.client("sqs", endpoint_url="http://localstack:4566/_aws/sqs/", region_name='us-east-1')

    # delete rogue message from queue
    sqs.delete_message(
        QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
    )
    print("Deleted rogue message:", message["MessageId"])

if __name__ == "__main__":
    time.sleep(30)
    while True:
        queue_url = "http://localstack:4566/000000000000/login-queue"

        sqs = boto3.client("sqs", endpoint_url="http://localstack:4566/_aws/sqs/", region_name='us-east-1')

        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=20
        )
        print(response)

        for message in response.get("Messages", []):
            try:
                # process message here
                print("Received message:", message["Body"])
                process_messages(message=message)

                # delete message from queue once successfully processed
                sqs.delete_message(
                    QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
                )
                print("Deleted message:", message["MessageId"])

            except Exception as e:
                print("Error processing message:", e)

                # check if message has been dequeued multiple times
                if message.get("Attributes", {}).get("ApproximateReceiveCount", 0) >= 5:
                    # message has been dequeued multiple times, delete it from queue
                    sqs.delete_message(
                        QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
                    )
                    print(
                        "Deleted message:",
                        message["MessageId"],
                        "after multiple retries",
                    )

        # sleep for a short interval before checking for more messages
        time.sleep(1)

    print("Thank you! See ya later...")
