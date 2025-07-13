from io import BytesIO
import logging
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


def get_file_from_minio(client: MinIOClientContext, s3_key: str, bucket: str = os.getenv("MINIO_BUCKET_NAME")) -> BytesIO:
    try:
        obj = client.get_object(Bucket=bucket, Key=s3_key)
        return obj["Body"]
    except Exception as e:
        raise RuntimeError(f"MinIO fetch failed: {e}")
    
    

def get_pdf_bytes_from_minio(client: MinIOClientContext, s3_key: str, bucket: str = os.getenv("MINIO_BUCKET_NAME")) -> BytesIO:
    """
    For internal PDF parsing (e.g. PyMuPDF). Returns BytesIO stream.
    """
    try:
        obj = client.get_object(Bucket=bucket, Key=s3_key)
        byte_stream = obj["Body"].read()  # read() returns full bytes
        return BytesIO(byte_stream)
    except Exception as e:
        raise RuntimeError(f"MinIO PDF bytes fetch failed: {e}")