import os
from pathlib import Path

import dj_database_url
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-local-only-key")
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "storages",
    "apps.accounts",
    "apps.wallet",
    "apps.payments",
    "apps.songs",
    "apps.core",
    "apps.dashboard",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv(
            "DATABASE_URL", "postgres://osp:osp_dev_password@localhost:5432/osp_music"
        ),
        conn_max_age=60,
    )
}
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
SITE_ID = 1
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_SIGNUP_FORM_CLASS = "apps.accounts.forms.OSPSignupForm"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_RATE_LIMITS = {"login": "10/m/ip", "signup": "10/m/ip"}
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{os.getenv('PUBLIC_BASE_URL', 'http://localhost:3000')}/account/verify-email/{{key}}",
    "account_reset_password_from_key": f"{os.getenv('PUBLIC_BASE_URL', 'http://localhost:3000')}/account/password/reset/key/{{key}}",
    "account_signup": f"{os.getenv('PUBLIC_BASE_URL', 'http://localhost:3000')}/account/signup",
}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English")]
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 10000},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SNIPPE_API_KEY = os.getenv("SNIPPE_API_KEY", "")
SNIPPE_WEBHOOK_SECRET = os.getenv("SNIPPE_WEBHOOK_SECRET", "")
SNIPPE_FAKE_MODE = False
SNIPPE_BASE_URL = os.getenv("SNIPPE_BASE_URL", "https://api.snippe.sh")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")
MUSIC_ENGINE = os.getenv("MUSIC_ENGINE", "fake")
MUREKA_API_KEY = os.getenv("MUREKA_API_KEY", "")
MUREKA_BASE_URL = os.getenv("MUREKA_BASE_URL", "https://api.mureka.ai")
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")
SUNO_BASE_URL = os.getenv("SUNO_BASE_URL", "")
MUREKA_JOB_TIMEOUT_SECONDS = int(os.getenv("MUREKA_JOB_TIMEOUT_SECONDS", "1200"))
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://host.docker.internal:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "osp-local")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "osp-local-secret")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "osp-music-songs")
MINIO_AUTO_CREATE_BUCKET = False
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "sweep-pending-payments-every-minute": {
        "task": "apps.payments.sweep_pending_payments",
        "schedule": 60.0,
    },
    "dispatch-song-jobs-every-five-seconds": {
        "task": "apps.songs.dispatch_jobs",
        "schedule": 5.0,
    },
    "poll-song-jobs-every-five-seconds": {
        "task": "apps.songs.poll_jobs",
        "schedule": 5.0,
    },
    "refresh-mureka-account-every-ten-minutes": {
        "task": "apps.songs.refresh_mureka_account",
        "schedule": 600.0,
    },
    "wallet-integrity-check-daily": {
        "task": "apps.wallet.check_wallet_integrity",
        "schedule": crontab(hour=3, minute=0),
    },
}
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "config.pagination.APIPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "config.authentication.SessionCookieAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "config.api_errors.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"support": "3/hour"},
}
