import uuid

from django.conf import settings
from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"
        VOIDED = "voided", "Voided"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short_id = models.CharField(max_length=24, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
        db_index=True,
    )
    amount_tzs = models.BigIntegerField()
    phone = models.CharField(max_length=15)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    snippe_reference = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    channel_provider = models.CharField(max_length=20, null=True, blank=True)
    fee_tzs = models.BigIntegerField(null=True, blank=True)
    confirmed_amount_tzs = models.BigIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    raw_create_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_tzs__gt=0),
                name="payment_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.short_id}: {self.amount_tzs} TZS"


class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=40)
    reference = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict)
    signature_valid = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type}: {self.event_id}"
