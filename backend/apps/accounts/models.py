import uuid
from typing import ClassVar

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .fields import CICharField, CIEmailField

display_name_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_]{3,30}$",
    message="Tumia herufi, namba au _ (alama 3 hadi 30).",
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have is_staff and is_superuser set")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = CIEmailField(unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    display_name = CICharField(
        max_length=30,
        unique=True,
        validators=[display_name_validator],
    )
    avatar = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(
        max_length=2,
        choices=[("sw", "Kiswahili"), ("en", "English")],
        default="sw",
    )
    theme = models.CharField(
        max_length=6,
        choices=[("system", "System"), ("light", "Light"), ("dark", "Dark")],
        default="system",
    )
    phone_last_used = models.CharField(max_length=15, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []
