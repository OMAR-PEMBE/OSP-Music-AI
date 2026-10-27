from __future__ import annotations

from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.payments.models import Payment
from apps.songs.models import SongJob

from .models import LedgerEntry, Wallet

BIGINT_MAX = 2**63 - 1
BIGINT_MIN = -(2**63)


class InsufficientBalance(APIException):
    status_code = 402
    default_detail = "Insufficient wallet balance."
    default_code = "insufficient_balance"


class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = "This key has already been used for another transaction."
    default_code = "duplicate_request"


def _validate_amount(amount_tzs: int, *, allow_zero: bool = False) -> None:
    if type(amount_tzs) is not int:
        raise ValueError("Amount must be an integer number of TZS.")
    if not allow_zero and amount_tzs == 0:
        raise ValueError("Amount must not be zero.")
    if not BIGINT_MIN <= amount_tzs <= BIGINT_MAX:
        raise ValueError("Amount is outside the PostgreSQL BIGINT range.")


def _matches_existing(entry, *, wallet, entry_type, amount_tzs, payment, song_job):
    return (
        entry.wallet_id == wallet.pk
        and entry.type == entry_type
        and entry.amount_tzs == amount_tzs
        and entry.payment_id == getattr(payment, "pk", None)
        and entry.song_job_id == getattr(song_job, "pk", None)
    )


def _apply_change(
    *,
    wallet: Wallet,
    amount_tzs: int,
    entry_type: str,
    idempotency_key: str,
    payment: Payment | None = None,
    song_job: SongJob | None = None,
    note: str = "",
    created_by=None,
) -> LedgerEntry:
    _validate_amount(amount_tzs)
    if not idempotency_key or len(idempotency_key) > 100:
        raise ValueError("Idempotency key must contain 1 to 100 characters.")

    with transaction.atomic():
        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        existing = LedgerEntry.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if _matches_existing(
                existing,
                wallet=locked_wallet,
                entry_type=entry_type,
                amount_tzs=amount_tzs,
                payment=payment,
                song_job=song_job,
            ):
                return existing
            raise IdempotencyConflict()

        new_balance = locked_wallet.balance_tzs + amount_tzs
        if new_balance < 0:
            raise InsufficientBalance()
        if new_balance > BIGINT_MAX:
            raise ValueError("Balance is outside the PostgreSQL BIGINT range.")

        locked_wallet.balance_tzs = new_balance
        locked_wallet.save(update_fields=["balance_tzs", "updated_at"])
        try:
            with transaction.atomic():
                return LedgerEntry.objects.create(
                    wallet=locked_wallet,
                    type=entry_type,
                    amount_tzs=amount_tzs,
                    balance_after_tzs=new_balance,
                    idempotency_key=idempotency_key,
                    payment=payment,
                    song_job=song_job,
                    note=note,
                    created_by=created_by,
                )
        except IntegrityError as exc:
            existing = LedgerEntry.objects.filter(
                idempotency_key=idempotency_key
            ).first()
            if existing and _matches_existing(
                existing,
                wallet=locked_wallet,
                entry_type=entry_type,
                amount_tzs=amount_tzs,
                payment=payment,
                song_job=song_job,
            ):
                return existing
            raise IdempotencyConflict() from exc


def credit_topup(payment: Payment) -> LedgerEntry:
    """Credit only an amount already confirmed as completed by the payments app."""
    if payment.status != Payment.Status.COMPLETED:
        raise ValueError("Only a completed payment can be credited.")
    if payment.confirmed_amount_tzs != payment.amount_tzs:
        raise ValueError("Confirmed payment amount must match the requested amount.")
    _validate_amount(payment.amount_tzs)
    wallet = Wallet.objects.get(user_id=payment.user_id)
    return _apply_change(
        wallet=wallet,
        amount_tzs=payment.amount_tzs,
        entry_type=LedgerEntry.Type.TOPUP,
        idempotency_key=f"topup:{payment.pk}",
        payment=payment,
    )


def charge_song(user, job: SongJob, price_tzs: int) -> LedgerEntry:
    _validate_amount(price_tzs)
    if job.user_id != user.pk:
        raise ValueError("A user can only charge their own song job.")
    if price_tzs != job.price_tzs:
        raise ValueError("The charge must use the song job's price snapshot.")
    wallet = Wallet.objects.get(user_id=user.pk)
    return _apply_change(
        wallet=wallet,
        amount_tzs=-price_tzs,
        entry_type=LedgerEntry.Type.SONG_CHARGE,
        idempotency_key=f"charge:{job.pk}",
        song_job=job,
    )


def refund_song(job: SongJob, amount_tzs: int) -> LedgerEntry | None:
    _validate_amount(amount_tzs, allow_zero=True)
    if amount_tzs == 0:
        return None
    if amount_tzs < 0 or amount_tzs > job.price_tzs:
        raise ValueError("Refund must be between zero and the song price.")
    wallet = Wallet.objects.get(user_id=job.user_id)
    return _apply_change(
        wallet=wallet,
        amount_tzs=amount_tzs,
        entry_type=LedgerEntry.Type.SONG_REFUND,
        idempotency_key=f"refund:{job.pk}",
        song_job=job,
    )


def settle_song_job(job: SongJob) -> LedgerEntry | None:
    """Refund failed versions once and mark the job settled in the same transaction."""
    with transaction.atomic():
        locked_job = SongJob.objects.select_for_update().get(pk=job.pk)
        if locked_job.settled_at:
            return None

        versions = locked_job.versions.all()
        if versions.count() != locked_job.versions_requested:
            raise ValueError(
                "All requested song versions must exist before settlement."
            )
        successful = versions.filter(status="ready").count()
        kept = (locked_job.price_tzs * successful) // locked_job.versions_requested
        refund_amount = locked_job.price_tzs - kept
        entry = refund_song(locked_job, refund_amount) if refund_amount > 0 else None
        locked_job.settled_at = timezone.now()
        locked_job.save(update_fields=["settled_at", "updated_at"])
        return entry


def adjust(wallet: Wallet, amount_tzs: int, note: str, staff_user) -> LedgerEntry:
    _validate_amount(amount_tzs)
    if not getattr(staff_user, "is_staff", False):
        raise PermissionError("Only staff users may adjust wallet balances.")
    if not isinstance(note, str) or len(note.strip()) < 10 or len(note.strip()) > 255:
        raise ValueError("Adjustment note must contain at least 10 characters.")
    return _apply_change(
        wallet=wallet,
        amount_tzs=amount_tzs,
        entry_type=LedgerEntry.Type.ADJUSTMENT,
        idempotency_key=f"adjust:{uuid4()}",
        note=note.strip(),
        created_by=staff_user,
    )
