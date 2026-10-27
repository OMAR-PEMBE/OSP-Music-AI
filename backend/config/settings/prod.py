import os

from .base import *

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
if R2_ACCOUNT_ID:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": os.getenv("R2_ACCESS_KEY_ID", ""),
                "secret_key": os.getenv("R2_SECRET_ACCESS_KEY", ""),
                "bucket_name": os.getenv("R2_BUCKET", "osp-music-songs"),
                "endpoint_url": f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                "region_name": "auto",
                "querystring_auth": True,
                "querystring_expire": 600,
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
