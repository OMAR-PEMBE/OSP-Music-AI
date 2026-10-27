import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.wallet.services import credit_topup

from .models import Payment
from .snippe_client import FakeSnippeClient, SnippeClient

logger = logging.getLogger(__name__)


def _snippe_client():
    if settings.DEBUG and settings.SNIPPE_FAKE_MODE:
        return FakeSnippeClient()
    return SnippeClient()


def new_short_id():
    # 24 chars and within Snippe's 30-character idempotency-key limit.
    return f"pay_{secrets.token_urlsafe(15)}"[:24]


def create_payment(user, *, amount_tzs, phone):
    payment = Payment.objects.create(
        short_id=new_short_id(),
        user=user,
        amount_tzs=amount_tzs,
        phone=phone,
    )
    try:
        response = _snippe_client().create_payment(payment)
        data = response.get("data") or {}
        reference = data.get("reference")
        if not isinstance(reference, str) or not reference:
            raise ValueError("Snippe create response omitted payment reference.")
        payment.snippe_reference = reference
        payment.expires_at = _parse_datetime(data.get("expires_at"))
        payment.raw_create_response = response
        payment.save(
            update_fields=[
                "snippe_reference",
                "expires_at",
                "raw_create_response",
                "updated_at",
            ]
        )
    except Exception as exc:
        payment.status = Payment.Status.FAILED
        payment.failure_reason = "provider_error"
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        logger.warning("Snippe payment creation failed for %s", payment.pk)
        raise PaymentProviderError from exc
    if settings.DEBUG and settings.SNIPPE_FAKE_MODE:
        payment = confirm_payment(payment)
    return payment


class PaymentProviderError(Exception):
    pass


def _parse_datetime(value):
    if not value:
        return None
    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _money_int(value):
    # bool is an int subclass but must never be accepted as a TZS amount.
    return value if type(value) is int else None


def _status_data(response):
    data = response.get("data") if isinstance(response, dict) else None
    return data if isinstance(data, dict) else {}


def confirm_payment(payment):
    """Ask Snippe for authoritative status, then settle atomically and once."""
    if not payment.snippe_reference:
        return payment
    try:
        response = _snippe_client().get_payment(payment.snippe_reference)
    except Exception:
        logger.exception("Could not confirm Snippe payment %s", payment.pk)
        return payment
    data = _status_data(response)
    status = data.get("status")
    amount = data.get("amount") or {}
    provider_amount = (
        _money_int(amount.get("value")) if isinstance(amount, dict) else None
    )
    currency = amount.get("currency") if isinstance(amount, dict) else None
    now = timezone.now()

    with transaction.atomic():
        locked = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked.status == Payment.Status.COMPLETED:
            return locked
        if status == "completed":
            if provider_amount != locked.amount_tzs or currency != "TZS":
                locked.failure_reason = "amount_mismatch"
                locked.save(update_fields=["failure_reason", "updated_at"])
                logger.error("Snippe amount mismatch for payment %s", locked.pk)
                return locked
            settlement = data.get("settlement") or {}
            fee = settlement.get("fees") if isinstance(settlement, dict) else None
            if isinstance(fee, dict):
                fee = fee.get("value", fee.get("amount"))
            locked.status = Payment.Status.COMPLETED
            locked.completed_at = _parse_datetime(data.get("completed_at")) or now
            locked.confirmed_amount_tzs = provider_amount
            locked.channel_provider = _provider_name(data)
            locked.fee_tzs = _money_int(fee)
            locked.failure_reason = None
            locked.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "confirmed_amount_tzs",
                    "channel_provider",
                    "fee_tzs",
                    "failure_reason",
                    "updated_at",
                ]
            )
            credit_topup(locked)
        elif status in {"failed", "voided", "expired"}:
            locked.status = status
            locked.failure_reason = str(data.get("failure_reason") or status)[:255]
            locked.save(update_fields=["status", "failure_reason", "updated_at"])
        return locked


def _provider_name(data):
    channel = data.get("channel") or {}
    return (
        str(channel.get("provider"))[:20]
        if isinstance(channel, dict) and channel.get("provider")
        else None
    )


def sweep_payments(*, now=None):
    now = now or timezone.now()
    older_than_five_hours = now - timedelta(hours=5)
    Payment.objects.filter(
        status=Payment.Status.PENDING,
        created_at__lt=older_than_five_hours,
    ).update(
        status=Payment.Status.EXPIRED, failure_reason="expired_locally", updated_at=now
    )
    payments = Payment.objects.filter(
        status=Payment.Status.PENDING,
        created_at__lte=now - timedelta(seconds=90),
        created_at__gte=older_than_five_hours,
    ).order_by("created_at")[:30]
    for payment in payments:
        confirm_payment(payment)
