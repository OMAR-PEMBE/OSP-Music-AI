import os

from .base import *

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SNIPPE_FAKE_MODE = os.getenv("SNIPPE_FAKE_MODE", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MINIO_AUTO_CREATE_BUCKET = True
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": os.getenv("MINIO_ACCESS_KEY", "osp-local"),
            "secret_key": os.getenv("MINIO_SECRET_KEY", "osp-local-secret"),
            "bucket_name": os.getenv("MINIO_BUCKET", "osp-music-songs"),
            "endpoint_url": os.getenv(
                "MINIO_ENDPOINT_URL", "http://host.docker.internal:9000"
            ),
            "region_name": "us-east-1",
            "signature_version": "s3v4",
            "addressing_style": "path",
            "querystring_auth": True,
            "querystring_expire": 600,
            "file_overwrite": True,
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
