import random
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections, transaction
from django.db.models import Sum
from django.test import Client
from django.urls import reverse

from apps.payments.models import Payment
from apps.songs.models import SongJob, SongVersion
from apps.wallet.models import LedgerEntry, Wallet
from apps.wallet.services import (
    InsufficientBalance,
    adjust,
    charge_song,
    credit_topup,
    settle_song_job,
)
from apps.wallet.tasks import check_wallet_integrity

pytestmark = pytest.mark.django_db


def make_user(*, staff=False):
    suffix = uuid4().hex[:12]
    return get_user_model().objects.create_user(
        email=f"wallet-{suffix}@example.test",
        password="SafePass_2026!",
        first_name="Wallet",
        last_name="Tester",
        display_name=f"Wallet_{suffix}",
        is_staff=staff,
    )


def make_wallet(*, balance=0):
    user = make_user()
    wallet = Wallet.objects.create(user=user)
    staff = make_user(staff=True)
    if balance:
        adjust(wallet, balance, "Initial test wallet funding", staff)
        wallet.refresh_from_db()
    return user, wallet, staff


def make_job(user, *, price=1000, version_statuses=None):
    job = SongJob.objects.create(user=user, price_tzs=price)
    statuses = version_statuses or [SongVersion.Status.PENDING] * 2
    for index, status in enumerate(statuses):
        SongVersion.objects.create(job=job, index=index, status=status)
    return job


def test_charge_with_sufficient_balance_is_recorded_once():
    user, wallet, staff = make_wallet(balance=1500)
    job = make_job(user, price=1000)

    entry = charge_song(user, job, 1000)
    repeated = charge_song(user, job, 1000)

    wallet.refresh_from_db()
    assert wallet.balance_tzs == 500
    assert entry.pk == repeated.pk
    assert entry.amount_tzs == -1000
    assert LedgerEntry.objects.filter(type=LedgerEntry.Type.SONG_CHARGE).count() == 1
    assert staff.is_staff


def test_insufficient_charge_rolls_back_job_and_creates_no_entry():
    user, wallet, _ = make_wallet()
    job_id = uuid4()

    with pytest.raises(InsufficientBalance), transaction.atomic():
        job = SongJob.objects.create(id=job_id, user=user, price_tzs=1000)
        SongVersion.objects.bulk_create(
            [
                SongVersion(job=job, index=0),
                SongVersion(job=job, index=1),
            ]
        )
        charge_song(user, job, 1000)

    assert not SongJob.objects.filter(pk=job_id).exists()
    assert not LedgerEntry.objects.exists()
    wallet.refresh_from_db()
    assert wallet.balance_tzs == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_charges_cannot_spend_the_same_balance_twice():
    user, wallet, staff = make_wallet(balance=1000)
    jobs = [make_job(user, price=700) for _ in range(2)]
    barrier = Barrier(2)

    def attempt(job_id):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            thread_user = get_user_model().objects.get(pk=user.pk)
            thread_job = SongJob.objects.get(pk=job_id)
            try:
                charge_song(thread_user, thread_job, 700)
                return "charged"
            except InsufficientBalance:
                return "insufficient"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [job.pk for job in jobs]))

    wallet.refresh_from_db()
    assert sorted(outcomes) == ["charged", "insufficient"]
    assert wallet.balance_tzs == 300
    assert LedgerEntry.objects.filter(type=LedgerEntry.Type.SONG_CHARGE).count() == 1
    assert staff.is_staff


def test_topup_credit_is_idempotent():
    _, wallet, _ = make_wallet()
    payment = Payment.objects.create(
        short_id="pay_" + uuid4().hex[:16],
        user=wallet.user,
        amount_tzs=3000,
        phone="255712345678",
        status=Payment.Status.COMPLETED,
        confirmed_amount_tzs=3000,
    )

    entry = credit_topup(payment)
    repeated = credit_topup(payment)

    wallet.refresh_from_db()
    assert wallet.balance_tzs == 3000
    assert entry.pk == repeated.pk
    assert LedgerEntry.objects.filter(type=LedgerEntry.Type.TOPUP).count() == 1


def test_settlement_run_twice_refunds_only_once():
    user, wallet, staff = make_wallet(balance=2000)
    job = make_job(user, price=1000, version_statuses=["ready", "failed"])
    charge_song(user, job, 1000)

    first = settle_song_job(job)
    second = settle_song_job(job)

    wallet.refresh_from_db()
    job.refresh_from_db()
    assert first is not None and first.amount_tzs == 500
    assert second is None
    assert job.settled_at is not None
    assert wallet.balance_tzs == 1500
    assert LedgerEntry.objects.filter(type=LedgerEntry.Type.SONG_REFUND).count() == 1
    assert staff.is_staff


def test_refund_amounts_for_zero_one_and_two_ready_versions():
    cases = [(0, 1000), (1, 500), (2, 0)]
    for ready_count, expected_refund in cases:
        user, wallet, staff = make_wallet(balance=1000)
        statuses = ["ready"] * ready_count + ["failed"] * (2 - ready_count)
        job = make_job(user, price=1000, version_statuses=statuses)
        charge_song(user, job, 1000)

        entry = settle_song_job(job)

        wallet.refresh_from_db()
        assert (entry.amount_tzs if entry else 0) == expected_refund
        assert wallet.balance_tzs == expected_refund
        assert staff.is_staff


def test_odd_price_refunds_half_up_for_one_ready_version():
    user, wallet, staff = make_wallet(balance=999)
    job = make_job(user, price=999, version_statuses=["ready", "failed"])
    charge_song(user, job, 999)

    entry = settle_song_job(job)

    wallet.refresh_from_db()
    assert entry.amount_tzs == 500
    assert wallet.balance_tzs == 500
    assert (
        LedgerEntry.objects.filter(
            wallet=wallet, type=LedgerEntry.Type.SONG_REFUND
        ).aggregate(total=Sum("amount_tzs"))["total"]
        == 500
    )
    assert staff.is_staff


def test_adjustment_that_would_make_balance_negative_is_rejected():
    _, wallet, staff = make_wallet()

    with pytest.raises(InsufficientBalance):
        adjust(wallet, -1, "Incorrect debit test", staff)

    wallet.refresh_from_db()
    assert wallet.balance_tzs == 0
    assert not LedgerEntry.objects.exists()


def test_balance_matches_ledger_after_two_hundred_random_adjustments():
    _, wallet, staff = make_wallet()
    rng = random.Random(20261027)
    expected_balance = 0

    for index in range(200):
        if expected_balance == 0 or rng.random() < 0.55:
            amount = rng.randint(1, 250)
        else:
            amount = -rng.randint(1, min(expected_balance, 250))
        adjust(wallet, amount, f"Random integrity adjustment {index:03d}", staff)
        expected_balance += amount

    wallet.refresh_from_db()
    total = sum(
        LedgerEntry.objects.filter(wallet=wallet).values_list("amount_tzs", flat=True)
    )
    assert wallet.balance_tzs == expected_balance == total
    assert LedgerEntry.objects.filter(wallet=wallet).count() == 200


def test_ledger_entries_reject_updates_and_deletes():
    _, wallet, staff = make_wallet(balance=100)
    entry = LedgerEntry.objects.filter(wallet=wallet).get()
    entry.note = "Tampered value"

    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        entry.delete()
    with pytest.raises(ValidationError):
        LedgerEntry.objects.filter(pk=entry.pk).update(note="Tampered value")
    with pytest.raises(ValidationError):
        LedgerEntry.objects.filter(pk=entry.pk).delete()

    entry.refresh_from_db()
    assert entry.note == "Initial test wallet funding"
    assert staff.is_staff


def test_integrity_task_reports_a_mismatched_wallet(caplog):
    _, wallet, _ = make_wallet()
    Wallet.objects.filter(pk=wallet.pk).update(balance_tzs=1)

    assert check_wallet_integrity() == 1
    assert "wallet_integrity_mismatch" in caplog.text


def test_wallet_endpoints_are_authenticated_and_private():
    user_a, wallet_a, staff = make_wallet(balance=150)
    user_b, wallet_b, staff_b = make_wallet(balance=90)
    EmailAddress.objects.create(
        user=user_a, email=user_a.email, verified=True, primary=True
    )
    EmailAddress.objects.create(
        user=user_b, email=user_b.email, verified=True, primary=True
    )
    client = Client()

    assert client.get("/api/wallet").status_code == 401
    unverified = make_user()
    Wallet.objects.create(user=unverified)
    client.force_login(unverified)
    unverified_response = client.get("/api/wallet")
    assert unverified_response.status_code == 403
    assert unverified_response.json()["error"]["code"] == "email_not_verified"

    client.force_login(user_a)
    balance_response = client.get("/api/wallet")
    history_response = client.get("/api/wallet/transactions?page=1")

    assert balance_response.status_code == 200
    assert balance_response.json() == {"balance_tzs": 150}
    assert history_response.status_code == 200
    payload = history_response.json()
    assert set(payload) == {"results", "next", "count"}
    rows = payload["results"]
    assert len(rows) == 1
    assert payload["count"] == 1 and payload["next"] is None
    assert rows[0]["amount_tzs"] == 150
    assert rows[0]["balance_after_tzs"] == 150
    assert all(row["amount_tzs"] != 90 for row in rows)
    assert wallet_b.user_id != wallet_a.user_id
    assert staff.is_staff and staff_b.is_staff


def test_admin_adjust_balance_action_records_a_ledger_entry():
    _, wallet, _ = make_wallet()
    staff = get_user_model().objects.create_superuser(
        email=f"admin-{uuid4().hex[:12]}@example.test",
        password="SafePass_2026!",
        first_name="Wallet",
        last_name="Admin",
        display_name=f"Admin_{uuid4().hex[:12]}",
    )
    client = Client()
    client.force_login(staff)
    changelist = reverse("admin:wallet_wallet_changelist")
    selection = {
        "action": "adjust_balance",
        "index": "0",
        "_selected_action": str(wallet.pk),
    }

    preview = client.post(changelist, selection)
    applied = client.post(
        changelist,
        {
            **selection,
            "apply_adjustment": "1",
            "amount_tzs": "250",
            "note": "Approved owner adjustment",
        },
    )

    wallet.refresh_from_db()
    entry = LedgerEntry.objects.get(wallet=wallet)
    assert preview.status_code == 200
    assert "Adjust wallet balance" in preview.content.decode()
    assert applied.status_code == 302
    assert wallet.balance_tzs == 250
    assert entry.created_by_id == staff.pk
    assert entry.note == "Approved owner adjustment"


def test_transaction_history_uses_shared_twenty_item_pagination():
    user, wallet, staff = make_wallet()
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    for index in range(21):
        adjust(wallet, 1, f"Pagination test credit {index:02d}", staff)
    client = Client()
    client.force_login(user)

    first_page = client.get("/api/wallet/transactions?page=1").json()
    second_page = client.get("/api/wallet/transactions?page=2").json()

    assert set(first_page) == {"results", "next", "count"}
    assert len(first_page["results"]) == 20
    assert first_page["count"] == 21 and first_page["next"] == 2
    assert len(second_page["results"]) == 1
    assert second_page["count"] == 21 and second_page["next"] is None
