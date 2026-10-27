import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet",
    )
    balance_tzs = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(balance_tzs__gte=0),
                name="wallet_balance_nonnegative",
            )
        ]

    def __str__(self):
        return f"{self.user_id}: {self.balance_tzs} TZS"


class LedgerEntryQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Ledger entries are append-only.")

    def delete(self):
        raise ValidationError("Ledger entries are append-only.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Ledger entries are append-only.")


class LedgerEntryManager(models.Manager.from_queryset(LedgerEntryQuerySet)):
    use_in_migrations = True


class LedgerEntry(models.Model):
    class Type(models.TextChoices):
        TOPUP = "topup", "Top-up"
        SONG_CHARGE = "song_charge", "Song charge"
        SONG_REFUND = "song_refund", "Song refund"
        ADJUSTMENT = "adjustment", "Adjustment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    amount_tzs = models.BigIntegerField()
    balance_after_tzs = models.BigIntegerField()
    idempotency_key = models.CharField(max_length=100, unique=True)
    payment = models.ForeignKey(
        "payments.Payment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    song_job = models.ForeignKey(
        "songs.SongJob",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="wallet_adjustments",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = LedgerEntryManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount_tzs=0),
                name="ledger_amount_nonzero",
            ),
            models.CheckConstraint(
                condition=Q(balance_after_tzs__gte=0),
                name="ledger_balance_after_nonnegative",
            ),
            models.CheckConstraint(
                condition=(~Q(type="topup") | Q(amount_tzs__gt=0)),
                name="ledger_topup_positive",
            ),
            models.CheckConstraint(
                condition=(~Q(type="song_charge") | Q(amount_tzs__lt=0)),
                name="ledger_song_charge_negative",
            ),
            models.CheckConstraint(
                condition=(~Q(type="song_refund") | Q(amount_tzs__gt=0)),
                name="ledger_song_refund_positive",
            ),
            models.CheckConstraint(
                condition=(~Q(type="topup") | Q(payment__isnull=False)),
                name="ledger_topup_payment_required",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(type__in=["song_charge", "song_refund"])
                    | Q(song_job__isnull=False)
                ),
                name="ledger_song_job_required",
            ),
            models.CheckConstraint(
                condition=(~Q(type="adjustment") | Q(created_by__isnull=False)),
                name="ledger_adjustment_staff_required",
            ),
            models.CheckConstraint(
                condition=(~Q(type="adjustment") | Q(note__regex=r"^.{10,255}$")),
                name="ledger_adjustment_note_required",
            ),
        ]
        indexes = [models.Index(fields=["wallet", "created_at"])]
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Ledger entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Ledger entries are append-only.")

    def __str__(self):
        return f"{self.type}: {self.amount_tzs} TZS ({self.wallet_id})"
