from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AppSettings
from apps.songs.models import LyricsRequest, SongJob
from apps.wallet.models import LedgerEntry, Wallet
from apps.wallet.services import adjust
from engines.base import SongRequest
from engines.mureka import MurekaEngine

pytestmark = pytest.mark.django_db


def make_user(*, balance=0):
    suffix = uuid4().hex[:12]
    user = get_user_model().objects.create_user(
        email=f"songs-{suffix}@example.test",
        password="SafePass_2026!",
        first_name="Song",
        last_name="Tester",
        display_name=f"Songs_{suffix}",
    )
    EmailAddress.objects.create(
        user=user, email=user.email, primary=True, verified=True
    )
    wallet = Wallet.objects.create(user=user)
    if balance:
        staff = get_user_model().objects.create_user(
            email=f"staff-{suffix}@example.test",
            password="SafePass_2026!",
            first_name="Test",
            last_name="Staff",
            display_name=f"Staff_{suffix}",
            is_staff=True,
        )
        adjust(wallet, balance, "Approved song test funding", staff)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, wallet, client


def song_payload(idea="Wimbo kwa Asha", **extra):
    return {
        "idea": idea,
        "genre": "bongo_flava",
        "language": "sw",
        "voice": "male",
        "lyrics": "",
        **extra,
    }


def create_song(client, *, idea="Wimbo kwa Asha", key=None, **extra):
    return client.post(
        "/api/songs",
        song_payload(idea, **extra),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(key or uuid4()),
    )


def process_fake_job(monkeypatch, job):
    from apps.songs.tasks import dispatch_jobs, poll_jobs, store_version

    def store_now(job_id, index, url, duration_ms=None):
        return store_version.run(job_id, index, url, duration_ms)

    monkeypatch.setattr("apps.songs.tasks.store_version.delay", store_now)
    assert dispatch_jobs.run() == 1
    for _ in range(4):
        poll_jobs.run()
        job.refresh_from_db()
        if job.settled_at:
            break
    job.refresh_from_db()
    return job


@pytest.fixture(autouse=True)
def fake_engine():
    with override_settings(MUSIC_ENGINE="fake"):
        yield


def test_fake_song_finishes_ready_and_charges_once(monkeypatch):
    user, wallet, client = make_user(balance=1000)
    response = create_song(client)
    job = SongJob.objects.get(pk=response.data["id"])

    job = process_fake_job(monkeypatch, job)
    audio_response = client.get(f"/api/songs/{job.pk}/versions/0/audio")
    download_response = client.get(f"/api/songs/{job.pk}/versions/0/audio?download=1")

    wallet.refresh_from_db()
    assert response.status_code == 201
    assert job.status == SongJob.Status.READY
    assert job.settled_at is not None
    assert list(job.versions.values_list("status", flat=True)) == ["ready", "ready"]
    assert wallet.balance_tzs == 0
    assert LedgerEntry.objects.filter(song_job=job, type="song_charge").count() == 1
    assert LedgerEntry.objects.filter(song_job=job, type="song_refund").count() == 0
    assert user.pk == job.user_id
    assert audio_response.status_code == 302
    assert "X-Amz-Expires=600" in audio_response["Location"]
    assert download_response.status_code == 302
    assert urlparse(download_response["Location"]).hostname == "localhost"
    assert urlparse(download_response["Location"]).port == 9000
    assert "response-content-disposition" in download_response["Location"].lower()


def test_fail1_returns_partial_and_refunds_half(monkeypatch):
    _user, wallet, client = make_user(balance=1000)
    response = create_song(client, idea="Wimbo #fail1")
    job = SongJob.objects.get(pk=response.data["id"])

    process_fake_job(monkeypatch, job)

    wallet.refresh_from_db()
    job.refresh_from_db()
    assert job.status == SongJob.Status.PARTIAL
    assert wallet.balance_tzs == 500
    assert (
        LedgerEntry.objects.filter(song_job=job, type="song_refund")
        .values_list("amount_tzs", flat=True)
        .get()
        == 500
    )


def test_fail2_returns_failed_and_refunds_full_price(monkeypatch):
    _user, wallet, client = make_user(balance=1000)
    response = create_song(client, idea="Wimbo #fail2")
    job = SongJob.objects.get(pk=response.data["id"])

    process_fake_job(monkeypatch, job)

    wallet.refresh_from_db()
    job.refresh_from_db()
    assert job.status == SongJob.Status.FAILED
    assert wallet.balance_tzs == 1000
    assert (
        LedgerEntry.objects.filter(song_job=job, type="song_refund")
        .values_list("amount_tzs", flat=True)
        .get()
        == 1000
    )


def test_timeout_refunds_after_configured_test_duration():
    _user, wallet, client = make_user(balance=1000)
    response = create_song(client, idea="Wimbo #timeout")
    job = SongJob.objects.get(pk=response.data["id"])
    from apps.songs.tasks import dispatch_jobs, poll_jobs

    assert dispatch_jobs.run() == 1
    SongJob.objects.filter(pk=job.pk).update(
        submitted_at=timezone.now() - timedelta(seconds=2)
    )
    with override_settings(MUREKA_JOB_TIMEOUT_SECONDS=1):
        poll_jobs.run()

    wallet.refresh_from_db()
    job.refresh_from_db()
    assert job.status == SongJob.Status.FAILED
    assert job.failure_reason == "timeout_ours"
    assert wallet.balance_tzs == 1000


def test_repeated_idempotency_key_returns_existing_job_without_second_charge():
    _user, wallet, client = make_user(balance=2000)
    key = uuid4()
    first = create_song(client, key=key)
    second = create_song(client, key=key)

    wallet.refresh_from_db()
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert SongJob.objects.count() == 1
    assert wallet.balance_tzs == 1000
    assert LedgerEntry.objects.filter(type=LedgerEntry.Type.SONG_CHARGE).count() == 1


def test_insufficient_balance_creates_no_job_or_charge():
    _user, wallet, client = make_user()

    response = create_song(client)

    wallet.refresh_from_db()
    assert response.status_code == 402
    assert response.data["error"]["code"] == "insufficient_balance"
    assert SongJob.objects.count() == 0
    assert not LedgerEntry.objects.exists()
    assert wallet.balance_tzs == 0


def test_lyrics_endpoint_is_free_and_enforces_ten_per_eat_day_limit():
    _user, _wallet, client = make_user()
    endpoint = "/api/lyrics"
    payload = {"idea": "Wimbo wa matumaini", "genre": "gospel", "language": "sw"}

    responses = [client.post(endpoint, payload, format="json") for _ in range(10)]
    limited = client.post(endpoint, payload, format="json")

    assert all(response.status_code == 200 for response in responses)
    assert responses[-1].data["remaining_today"] == 0
    assert limited.status_code == 429
    assert limited.data["error"]["code"] == "lyrics_limit_reached"
    assert LyricsRequest.objects.count() == 10
    assert LyricsRequest.objects.filter(success=True).count() == 10
    assert not LedgerEntry.objects.exists()


def test_users_cannot_read_or_download_another_users_song():
    _owner, _wallet, owner_client = make_user(balance=1000)
    _other, _other_wallet, other_client = make_user(balance=1000)
    created = create_song(owner_client)
    job_id = created.data["id"]

    detail = other_client.get(f"/api/songs/{job_id}")
    audio = other_client.get(f"/api/songs/{job_id}/versions/0/audio")

    assert detail.status_code == 404
    assert audio.status_code == 404


def test_song_rename_delete_and_mark_seen_are_owner_scoped():
    user, _wallet, client = make_user(balance=1000)
    created = create_song(client)
    job = SongJob.objects.get(pk=created.data["id"])

    renamed = client.patch(
        f"/api/songs/{job.pk}", {"title": "Asha mpya"}, format="json"
    )
    marked_seen = client.post("/api/songs/mark-seen")
    deleted = client.delete(f"/api/songs/{job.pk}")
    job.refresh_from_db()

    assert renamed.status_code == 200
    assert renamed.data["title"] == "Asha mpya"
    assert marked_seen.status_code == 204
    assert job.seen_by_user is True
    assert deleted.status_code == 204
    assert job.deleted_at is not None
    assert not SongJob.objects.filter(user=user, deleted_at__isnull=True).exists()


def test_mureka_engine_maps_documented_song_request_and_query_shapes():
    class MockClient:
        last_trace_id = "trace-test"

        def __init__(self):
            self.calls = []

        def request(self, method, path, *, body=None):
            self.calls.append((method, path, body))
            if path == "/v1/song/generate":
                return {"id": "mureka-task-1", "status": "queued"}
            return {
                "id": "mureka-task-1",
                "status": "succeeded",
                "choices": [
                    {
                        "index": 0,
                        "id": "song-a",
                        "url": "https://example.test/a.mp3",
                        "duration": 1200,
                    },
                    {
                        "index": 1,
                        "id": "song-b",
                        "url": "https://example.test/b.mp3",
                        "duration": 1300,
                    },
                ],
            }

    client = MockClient()
    engine = MurekaEngine(client=client)
    request = SongRequest(
        job_id=str(uuid4()),
        idea="Wimbo wa Asha",
        lyrics="[Verse] Habari Asha",
        model="mureka-9",
        prompt="bongo flava, swahili lyrics, female vocal",
        voice="female",
    )

    task_id = engine.submit_song(request)
    result = engine.get_status(task_id)

    method, path, body = client.calls[0]
    assert (method, path) == ("POST", "/v1/song/generate")
    assert body == {
        "lyrics": request.lyrics,
        "model": "mureka-9",
        "prompt": request.prompt,
        "n": 2,
        "stream": True,
        "gender": "female",
    }
    assert result.status == "succeeded"
    assert result.choices[1].provider_song_id == "song-b"
    assert result.choices[1].duration_ms == 1300
    assert engine.last_trace_id == "trace-test"


def test_appsettings_is_singleton_with_documented_defaults():
    settings = AppSettings.objects.create()

    assert settings.pk == 1
    assert settings.song_price_tzs == 1000
    assert settings.mureka_model == "mureka-9"
    assert settings.lyrics_daily_limit == 10
    assert AppSettings.objects.count() == 1


def test_active_engine_can_switch_to_suno_and_complete_with_fake_engine(monkeypatch):
    app_settings = AppSettings.objects.get_or_create(pk=1)[0]
    with override_settings(SUNO_API_KEY="fake-suno-key"):
        app_settings.active_engine = "suno"
        app_settings.suno_cost_per_version_usd_cents = Decimal("2.00")
        app_settings.save()
        _user, wallet, client = make_user(balance=1000)
        response = create_song(client)
        job = SongJob.objects.get(pk=response.data["id"])

        assert response.status_code == 201
        assert job.engine == SongJob.Engine.SUNO
        job = process_fake_job(monkeypatch, job)

    wallet.refresh_from_db()
    assert job.engine == SongJob.Engine.SUNO
    assert job.status == SongJob.Status.READY
    assert job.settled_at is not None
    assert wallet.balance_tzs == 0


def test_low_mureka_balance_falls_back_to_suno_and_settles(monkeypatch):
    app_settings = AppSettings.objects.get_or_create(pk=1)[0]
    with override_settings(SUNO_API_KEY="fake-suno-key"):
        app_settings.active_engine = "mureka"
        app_settings.fallback_engine = "suno"
        app_settings.mureka_balance_usd_cents = 0
        app_settings.suno_cost_per_version_usd_cents = Decimal("2.00")
        app_settings.save()
        _user, wallet, client = make_user(balance=1000)
        response = create_song(client)
        job = SongJob.objects.get(pk=response.data["id"])

        assert job.engine == SongJob.Engine.MUREKA
        job = process_fake_job(monkeypatch, job)

    wallet.refresh_from_db()
    assert job.engine == SongJob.Engine.SUNO
    assert job.status == SongJob.Status.READY
    assert job.settled_at is not None
    assert wallet.balance_tzs == 0


def test_provider_capacity_timeout_uses_configured_fake_fallback():
    from django.utils import timezone

    from engines.router import get_engine_for_new_job

    app_settings = AppSettings.objects.get_or_create(pk=1)[0]
    with override_settings(SUNO_API_KEY="fake-suno-key"):
        app_settings.active_engine = "mureka"
        app_settings.fallback_engine = "suno"
        app_settings.mureka_balance_usd_cents = None
        app_settings.suno_cost_per_version_usd_cents = Decimal("2.00")
        app_settings.save()
        engine = get_engine_for_new_job(
            preferred_engine="mureka",
            app_settings=app_settings,
            capacity_error_since=timezone.now() - timedelta(minutes=3),
        )

    assert engine.name == SongJob.Engine.SUNO


def test_suno_requires_key_cost_and_margin_before_admin_activation():
    app_settings = AppSettings(active_engine="suno")
    app_settings.suno_cost_per_version_usd_cents = Decimal("2.00")
    with (
        override_settings(SUNO_API_KEY=""),
        pytest.raises(ValidationError, match="SUNO_API_KEY"),
    ):
        app_settings.save()

    app_settings = AppSettings(active_engine="suno")
    with (
        override_settings(SUNO_API_KEY="configured-key"),
        pytest.raises(ValidationError, match="per-version cost"),
    ):
        app_settings.save()

    app_settings = AppSettings(
        active_engine="suno",
        suno_cost_per_version_usd_cents=Decimal("20.00"),
    )
    with (
        override_settings(SUNO_API_KEY="configured-key"),
        pytest.raises(ValidationError, match="60% margin"),
    ):
        app_settings.save()


def test_mureka_low_balance_does_not_disable_global_generation(monkeypatch):
    from apps.songs.tasks import refresh_mureka_account

    app_settings = AppSettings.objects.get_or_create(pk=1)[0]
    app_settings.generation_enabled = True
    app_settings.mureka_balance_usd_cents = None
    app_settings.save()
    monkeypatch.setattr(
        "engines.mureka.MurekaEngine.refresh_account",
        lambda _engine: {
            "balance_usd_cents": 1,
            "concurrent_request_limit": 2,
        },
    )
    with override_settings(MUSIC_ENGINE="mureka", MUREKA_API_KEY="configured-key"):
        assert refresh_mureka_account.run() == 2

    app_settings.refresh_from_db()
    assert app_settings.generation_enabled is True
    assert app_settings.mureka_balance_usd_cents == 1
