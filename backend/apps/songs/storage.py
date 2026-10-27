from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def ensure_minio_bucket():
    if not settings.MINIO_AUTO_CREATE_BUCKET:
        return
    bucket = settings.MINIO_BUCKET
    client = boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT_URL,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",
    )
    existing = {entry["Name"] for entry in client.list_buckets().get("Buckets", [])}
    if bucket not in existing:
        try:
            client.create_bucket(Bucket=bucket)
        except ClientError as create_exc:
            create_code = str(create_exc.response.get("Error", {}).get("Code", ""))
            if create_code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                raise


def _read_audio(url):
    if url == "fake://sample.mp3":
        fixture = Path(settings.BASE_DIR) / "tests" / "fixtures" / "sample.mp3"
        return fixture.read_bytes()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Provider audio URL must use HTTPS.")
    with urlopen(url, timeout=60) as response:
        data = response.read()
    if not data:
        raise ValueError("Provider returned an empty audio file.")
    return data


def store_audio_version(job, version, url, duration_ms=None):
    ensure_minio_bucket()
    content = _read_audio(url)
    key = f"songs/{job.user_id}/{job.pk}/{version.index}.mp3"
    saved_key = default_storage.save(key, ContentFile(content))
    version.storage_key = saved_key
    version.size_bytes = len(content)
    version.duration_ms = duration_ms
    return version


def signed_audio_url(storage_key, *, parameters=None, expire=600):
    public_endpoint_url = getattr(settings, "MINIO_PUBLIC_ENDPOINT_URL", "")
    if public_endpoint_url:
        client = boto3.client(
            "s3",
            endpoint_url=public_endpoint_url,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.MINIO_BUCKET,
                "Key": storage_key,
                **(parameters or {}),
            },
            ExpiresIn=expire,
        )

    try:
        return default_storage.url(
            storage_key,
            parameters=parameters,
            expire=expire,
        )
    except TypeError:
        return default_storage.url(storage_key)
