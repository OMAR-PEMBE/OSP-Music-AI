from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.core.models import get_app_settings
from apps.payments.models import Payment
from apps.songs.models import LyricsRequest, SongJob, SongVersion
from apps.wallet.models import Wallet
from apps.wallet.services import charge_song, credit_topup, settle_song_job

pytestmark = pytest.mark.django_db


def make_user(*, staff=False):
    suffix = uuid4().hex[:12]
    return get_user_model().objects.create_user(
        email=f"dashboard-{suffix}@example.test",
        password="test-password-123",
        first_name="Dashboard",
        last_name="Tester",
        display_name=f"Dash_{suffix}",
        is_staff=staff,
        is_superuser=staff,
    )


def test_daily_summary_reports_money_job_cost_and_low_balance():
    staff = make_user(staff=True)
    user = make_user()
    wallet = Wallet.objects.create(user=user)
    payment = Payment.objects.create(
        short_id=f"pay_{uuid4().hex[:12]}",
        user=user,
        amount_tzs=3000,
        phone="255700000001",
        status=Payment.Status.COMPLETED,
        confirmed_amount_tzs=3000,
    )
    credit_topup(payment)
    LyricsRequest.objects.create(user=user, prompt="Song prompt", success=True)

    job = SongJob.objects.create(
        user=user,
        price_tzs=1000,
        est_cost_usd_cents=10,
        status=SongJob.Status.PARTIAL,
        finished_at=timezone.now(),
    )
    SongVersion.objects.create(job=job, index=0, status=SongVersion.Status.READY)
    SongVersion.objects.create(job=job, index=1, status=SongVersion.Status.FAILED)
    charge_song(user, job, 1000)
    settle_song_job(job)

    app_settings = get_app_settings()
    app_settings.mureka_balance_usd_cents = 1900
    app_settings.save(update_fields=["mureka_balance_usd_cents"])

    client = Client()
    client.force_login(staff)
    response = client.get("/admin/summary/")

    assert response.status_code == 200
    assert response.context["songs_generated"] == 1
    assert response.context["jobs_with_failed_versions"] == 1
    assert b"New users" in response.content
    assert b"Confirmed top-ups" in response.content
    assert b"TZS 3000" in response.content
    assert b"Songs generated" in response.content
    assert b"TZS 500" in response.content
    assert b"TZS 288" in response.content
    assert b"TZS 212" in response.content
    assert b"USD 19.00" in response.content
    assert b"below the configured low-balance threshold" in response.content
    wallet.refresh_from_db()
    assert wallet.balance_tzs == 2500


def test_daily_summary_requires_staff_access():
    anonymous_response = Client().get("/admin/summary/")

    staff = make_user(staff=True)
    customer = make_user()
    client = Client()
    client.force_login(customer)
    customer_response = client.get("/admin/summary/")
    client.force_login(staff)
    user_list_response = client.get("/admin/accounts/user/")
    user_detail_response = client.get(f"/admin/accounts/user/{customer.pk}/change/")

    assert anonymous_response.status_code == 302
    assert customer_response.status_code == 302
    assert user_list_response.status_code == 200
    assert user_detail_response.status_code == 200


def test_song_job_admin_rechecks_only_pollable_jobs():
    staff = make_user(staff=True)
    user = make_user()
    active_job = SongJob.objects.create(
        user=user,
        price_tzs=1000,
        status=SongJob.Status.RUNNING,
        provider_task_id=f"provider-{uuid4().hex[:16]}",
    )
    queued_job = SongJob.objects.create(
        user=user,
        price_tzs=1000,
        status=SongJob.Status.QUEUED,
    )

    client = Client()
    client.force_login(staff)
    with patch("apps.songs.tasks._poll_one") as poll_one:
        response = client.post(
            "/admin/songs/songjob/",
            {
                "action": "recheck_status",
                "index": "0",
                "_selected_action": [str(active_job.pk), str(queued_job.pk)],
            },
            follow=True,
        )

    assert response.status_code == 200
    poll_one.assert_called_once()
    assert poll_one.call_args.args[0].pk == active_job.pk
    assert b"No generation was resubmitted" in response.content
    assert b"Skipped 1 job(s)" in response.content


def test_payment_admin_needs_review_filter_finds_amount_mismatches():
    staff = make_user(staff=True)
    user = make_user()
    mismatch = Payment.objects.create(
        short_id=f"pay_{uuid4().hex[:12]}",
        user=user,
        amount_tzs=1000,
        phone="255700000002",
        status=Payment.Status.FAILED,
        failure_reason="amount_mismatch",
    )
    ordinary = Payment.objects.create(
        short_id=f"pay_{uuid4().hex[:12]}",
        user=user,
        amount_tzs=2000,
        phone="255700000003",
        status=Payment.Status.FAILED,
        failure_reason="provider_error",
    )

    client = Client()
    client.force_login(staff)
    response = client.get("/admin/payments/payment/?needs_review=yes")

    assert response.status_code == 200
    assert mismatch.short_id.encode() in response.content
    assert ordinary.short_id.encode() not in response.content
