import boto3
from botocore.config import Config
from django.conf import settings


def get_backup_storage_client():
    return boto3.client(
        "s3",
        endpoint_url=(f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"),
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )
