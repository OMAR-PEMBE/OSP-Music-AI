import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.payments.models import Payment, WebhookEvent
from apps.payments.services import confirm_payment, sweep_payments
from apps.payments.snippe_client import SnippeClient, SnippeNetworkError
from apps.payments.tasks import process_snippe_event
from apps.wallet.models import LedgerEntry, Wallet

pytestmark = pytest.mark.django_db


def make_user():
    suffix = uuid4().hex[:12]
    user = get_user_model().objects.create_user(
        email=f"payment-{suffix}@example.test",
        password="SafePass_2026!",
        first_name="Payment",
        last_name="Tester",
        display_name=f"Payment_{suffix}",
    )
    EmailAddress.objects.create(
        user=user, email=user.email, primary=True, verified=True
    )
    wallet = Wallet.objects.create(user=user)
    return user, wallet


def make_payment(user, *, status=Payment.Status.PENDING, created_at=None):
    payment = Payment.objects.create(
        short_id=f"pay_{uuid4().hex[:16]}",
        user=user,
        amount_tzs=1000,
        phone="255712345678",
        status=status,
        snippe_reference=f"ref_{uuid4().hex[:12]}",
    )
    if created_at:
        Payment.objects.filter(pk=payment.pk).update(created_at=created_at)
        payment.refresh_from_db()
    return payment


def provider_response(status="completed", *, amount=1000, currency="TZS"):
    return {
        "data": {
            "status": status,
            "amount": {"value": amount, "currency": currency},
            "completed_at": "2026-10-27T10:00:00Z",
            "channel": {"provider": "mpesa"},
            "settlement": {"fees": {"value": 25}},
        }
    }


def send_webhook(client, payment, *, timestamp=None, signature=None):
    timestamp = str(timestamp or int(time.time()))
    payload = {
        "id": f"evt_{uuid4().hex}",
        "type": "payment.completed",
        "data": {"reference": payment.snippe_reference},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    expected = hmac.new(
        b"test-webhook-secret",
        timestamp.encode() + b"." + raw,
        hashlib.sha256,
    ).hexdigest()
    response = client.post(
        "/webhooks/snippe",
        data=raw,
        content_type="application/json",
        HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
        HTTP_X_WEBHOOK_SIGNATURE=signature or expected,
    )
    return response, payload


@pytest.fixture(autouse=True)
def webhook_secret(settings):
    settings.SNIPPE_WEBHOOK_SECRET = "test-webhook-secret"
    settings.SNIPPE_FAKE_MODE = False


def test_valid_webhook_confirms_and_credits_once(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user)
    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment",
        lambda _self, _reference: provider_response(),
    )
    monkeypatch.setattr(
        "apps.payments.views.process_snippe_event.delay", lambda _pk: None
    )

    response, payload = send_webhook(Client(), payment)
    event = WebhookEvent.objects.get(event_id=payload["id"])
    process_snippe_event.run(str(event.pk))
    confirm_payment(payment)

    wallet.refresh_from_db()
    payment.refresh_from_db()
    assert response.status_code == 200
    assert payment.status == Payment.Status.COMPLETED
    assert wallet.balance_tzs == 1000
    assert LedgerEntry.objects.filter(payment=payment).count() == 1


def test_duplicate_webhook_deliveries_are_deduplicated(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user)
    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment",
        lambda _self, _reference: provider_response(),
    )
    monkeypatch.setattr(
        "apps.payments.views.process_snippe_event.delay", lambda _pk: None
    )
    client = Client()
    first, payload = send_webhook(client, payment)
    raw = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"test-webhook-secret", timestamp.encode() + b"." + raw, hashlib.sha256
    ).hexdigest()
    for _ in range(2):
        response = client.post(
            "/webhooks/snippe",
            data=raw,
            content_type="application/json",
            HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
            HTTP_X_WEBHOOK_SIGNATURE=signature,
        )
        assert response.status_code == 200
    event = WebhookEvent.objects.get(event_id=payload["id"])
    process_snippe_event.run(str(event.pk))
    process_snippe_event.run(str(event.pk))

    wallet.refresh_from_db()
    assert first.status_code == 200
    assert WebhookEvent.objects.filter(event_id=payload["id"]).count() == 1
    assert wallet.balance_tzs == 1000
    assert LedgerEntry.objects.filter(payment=payment).count() == 1


def test_bad_signature_is_stored_and_never_credits(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user)
    response, payload = send_webhook(Client(), payment, signature="0" * 64)

    assert response.status_code == 400
    assert not WebhookEvent.objects.get(event_id=payload["id"]).signature_valid
    wallet.refresh_from_db()
    assert wallet.balance_tzs == 0


def test_old_webhook_timestamp_is_rejected(monkeypatch):
    user, _wallet = make_user()
    payment = make_payment(user)
    response, _payload = send_webhook(
        Client(), payment, timestamp=int(time.time()) - 301
    )
    assert response.status_code == 400


def test_webhook_does_not_override_provider_pending_status(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user)
    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment",
        lambda _self, _reference: provider_response("pending"),
    )

    confirm_payment(payment)

    payment.refresh_from_db()
    wallet.refresh_from_db()
    assert payment.status == Payment.Status.PENDING
    assert wallet.balance_tzs == 0


def test_amount_mismatch_is_flagged_without_credit(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user)
    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment",
        lambda _self, _reference: provider_response(amount=999),
    )

    confirm_payment(payment)

    payment.refresh_from_db()
    wallet.refresh_from_db()
    assert payment.status == Payment.Status.PENDING
    assert payment.failure_reason == "amount_mismatch"
    assert wallet.balance_tzs == 0


def test_sweeper_confirms_missed_webhook(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user, created_at=timezone.now() - timedelta(minutes=2))
    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment",
        lambda _self, _reference: provider_response(),
    )

    sweep_payments()

    payment.refresh_from_db()
    wallet.refresh_from_db()
    assert payment.status == Payment.Status.COMPLETED
    assert wallet.balance_tzs == 1000


@pytest.mark.django_db(transaction=True)
def test_webhook_task_and_sweeper_settle_concurrently_once(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user, created_at=timezone.now() - timedelta(minutes=2))
    event = WebhookEvent.objects.create(
        event_id=f"evt_{uuid4().hex}",
        event_type="payment.completed",
        reference=payment.snippe_reference,
        payload={},
        signature_valid=True,
    )
    barrier = Barrier(2)

    def confirmed_response(_self, _reference):
        barrier.wait(timeout=10)
        return provider_response()

    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment", confirmed_response
    )

    def run_webhook():
        close_old_connections()
        try:
            process_snippe_event.run(str(event.pk))
        finally:
            connections.close_all()

    def run_sweeper():
        close_old_connections()
        try:
            sweep_payments()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_webhook), pool.submit(run_sweeper)]
        for future in futures:
            future.result(timeout=20)

    wallet.refresh_from_db()
    assert wallet.balance_tzs == 1000
    assert LedgerEntry.objects.filter(payment=payment).count() == 1


def test_failed_payment_does_not_change_wallet(monkeypatch):
    user, wallet = make_user()
    payment = make_payment(user)
    monkeypatch.setattr(
        "apps.payments.services.SnippeClient.get_payment",
        lambda _self, _reference: provider_response("failed"),
    )

    confirm_payment(payment)

    payment.refresh_from_db()
    wallet.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert wallet.balance_tzs == 0
    assert not LedgerEntry.objects.filter(payment=payment).exists()


def test_user_cannot_read_another_users_topup():
    user_a, _wallet_a = make_user()
    user_b, _wallet_b = make_user()
    payment_b = make_payment(user_b)
    client = APIClient()
    client.force_authenticate(user=user_a)

    response = client.get(reverse("wallet-topup-detail", args=[payment_b.pk]))

    assert response.status_code == 404


def test_snippe_network_retry_uses_same_idempotency_key(monkeypatch):
    user, _wallet = make_user()
    payment = make_payment(user)
    client = SnippeClient(api_key="test-key")
    idempotency_keys = []
    calls = 0

    def request(_method, _path, *, body=None, idempotency_key=None):
        nonlocal calls
        calls += 1
        idempotency_keys.append(idempotency_key)
        if calls < 3:
            raise SnippeNetworkError("temporary network failure")
        return {"data": {"reference": "snippe-ref"}}

    monkeypatch.setattr(client, "_request", request)

    response = client.create_payment(payment)

    assert response["data"]["reference"] == "snippe-ref"
    assert calls == 3
    assert idempotency_keys == [payment.short_id] * 3


def test_topup_creation_normalizes_phone_and_returns_polling_fields(monkeypatch):
    user, _wallet = make_user()
    monkeypatch.setattr(
        "apps.payments.snippe_client.SnippeClient.create_payment",
        lambda _self, _payment: {
            "data": {
                "reference": "snippe-reference",
                "expires_at": "2026-10-27T11:00:00Z",
            }
        },
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse("wallet-topups"),
        {"amount_tzs": 1000, "phone": "+255 712 345 678"},
        format="json",
    )

    payment = Payment.objects.get(user=user)
    assert response.status_code == 201
    assert payment.phone == "255712345678"
    assert payment.snippe_reference == "snippe-reference"
    assert set(response.data) == {
        "id",
        "amount_tzs",
        "phone_masked",
        "status",
        "created_at",
        "completed_at",
    }


def test_local_fake_topup_credits_only_through_confirmed_wallet_service():
    user, wallet = make_user()
    client = APIClient()
    client.force_authenticate(user=user)

    with override_settings(DEBUG=True, SNIPPE_FAKE_MODE=True):
        response = client.post(
            reverse("wallet-topups"),
            {"amount_tzs": 1000, "phone": "0712345678"},
            format="json",
        )

    payment = Payment.objects.get(user=user)
    wallet.refresh_from_db()
    assert response.status_code == 201
    assert response.data["status"] == Payment.Status.COMPLETED
    assert payment.confirmed_amount_tzs == 1000
    assert wallet.balance_tzs == 1000
    assert LedgerEntry.objects.filter(payment=payment).count() == 1
