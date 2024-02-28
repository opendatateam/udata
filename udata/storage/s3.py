import boto3
from flask import current_app
import json

def get_client():
    url = current_app.config.get('S3_URL')
    if url is None:
        raise ValueError('No S3_URL provided')
    
    access_key_id = current_app.config.get('S3_ACCESS_KEY_ID')
    if access_key_id is None:
        raise ValueError('No S3_ACCESS_KEY_ID provided')
    
    secret_access_key = current_app.config.get('S3_SECRET_ACCESS_KEY')
    if secret_access_key is None:
        raise ValueError('No S3_SECRET_ACCESS_KEY provided')

    return boto3.client(
        "s3",
        endpoint_url=url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )

def store_bytes(bucket: str, filename: str, bytes: bytes):
    get_client().put_object(
        Bucket=bucket,
        Key=filename,
        Body=bytes,
    )

def store_as_json(bucket: str, filename: str, value):
    store_bytes(bucket, filename, bytes(json.dumps(value).encode('UTF-8')))

def get_bytes(bucket: str, filename: str) -> bytes:
    get_client().get_object(Bucket=bucket, Key=filename)


def get_from_json(bucket: str, filename: str) -> bytes:
    json.loads(get_bytes(bucket, filename).decode('utf-8'))