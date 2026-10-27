import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 50 characters.")

if not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL must be configured in production.")
if not os.getenv("REDIS_URL"):
    raise ImproperlyConfigured("REDIS_URL must be configured in production.")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
if not PUBLIC_BASE_URL.startswith("https://"):
    raise ImproperlyConfigured("PUBLIC_BASE_URL must use HTTPS in production.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list production hostnames.")

if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS must list HTTPS production origins."
    )

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = 31536000

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "")
R2_BACKUP_BUCKET = os.getenv("R2_BACKUP_BUCKET", "")
if not all(
    [R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_BACKUP_BUCKET]
):
    raise ImproperlyConfigured("All production Cloudflare R2 settings are required.")

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "bucket_name": R2_BUCKET,
            "endpoint_url": f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            "region_name": "auto",
            "signature_version": "s3v4",
            "addressing_style": "path",
            "querystring_auth": True,
            "querystring_expire": 600,
            "file_overwrite": False,
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
STATIC_ROOT = BASE_DIR / "staticfiles"

MUSIC_ENGINE = os.getenv("MUSIC_ENGINE", "mureka")
if MUSIC_ENGINE != "mureka":
    raise ImproperlyConfigured(
        "Production MUSIC_ENGINE must be mureka; fake generation is not safe."
    )
if not os.getenv("MUREKA_API_KEY"):
    raise ImproperlyConfigured("MUREKA_API_KEY must be configured in production.")
if not os.getenv("SNIPPE_API_KEY") or not os.getenv("SNIPPE_WEBHOOK_SECRET"):
    raise ImproperlyConfigured(
        "SNIPPE_API_KEY and SNIPPE_WEBHOOK_SECRET are required in production."
    )
if not all(
    [
        os.getenv("EMAIL_HOST"),
        os.getenv("EMAIL_HOST_USER"),
        os.getenv("EMAIL_HOST_PASSWORD"),
        os.getenv("DEFAULT_FROM_EMAIL"),
    ]
):
    raise ImproperlyConfigured("Production SMTP settings are required.")
