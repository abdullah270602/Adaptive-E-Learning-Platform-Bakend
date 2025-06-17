# app/services/minio_client.py

import boto3
import os

class MinIOClientContext:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT")
        self.access_key = os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = os.getenv("MINIO_SECRET_KEY")

    def __enter__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1"
        )
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"MinIO client context exited with error: {exc_val}")
        return False
