import re
from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client

from apps.core.models import SupportMessage
from apps.songs.models import LyricsRequest, SongJob, SongVersion
from apps.songs.services import fail_job, finalize_job
from apps.songs.tasks import dispatch_jobs
from apps.wallet.models import LedgerEntry, Wallet
from apps.wallet.services import adjust, charge_song

pytestmark = pytest.mark.django_db

AUTH = "/api/auth/browser/v1/auth"


def signup(client, email="omar@example.test", display_name="OmarMusic"):
    return client.post(
        f"{AUTH}/signup",
        data={
            "email": email,
            "password": "SafePass_2026!",
            "first_name": "Omar",
            "last_name": "Mussa",
            "display_name": display_name,
        },
        content_type="application/json",
    )


def test_signup_verification_login_and_password_reset(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    client = Client()

    response = signup(client)
    assert response.status_code == 401, response.content
    user = get_user_model().objects.get(email="omar@example.test")
    assert user.language == "en"
    assert Wallet.objects.get(user=user).balance_tzs == 0
    assert EmailAddress.objects.filter(user=user, verified=False).exists()
    assert mail.outbox

    confirmation = EmailConfirmationHMAC.create(
        EmailAddress.objects.get(user=user, email=user.email)
    )
    response = client.post(
        f"{AUTH}/email/verify",
        data={"key": confirmation.key},
        content_type="application/json",
    )
    assert response.status_code == 401, response.content
    assert EmailAddress.objects.get(user=user, email=user.email).verified

    response = client.post(
        f"{AUTH}/login",
        data={"email": user.email, "password": "SafePass_2026!"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    assert client.get("/api/me").json()["email"] == user.email

    mail.outbox.clear()
    response = client.post(
        f"{AUTH}/password/request",
        data={"email": user.email},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    assert mail.outbox
    reset_key_match = re.search(r"/key/([^\s/]+)", mail.outbox[-1].body)
    assert reset_key_match, mail.outbox[-1].body
    response = client.post(
        f"{AUTH}/password/reset",
        data={"key": reset_key_match.group(1), "password": "NewSafePass_2026!"},
        content_type="application/json",
    )
    assert response.status_code == 401, response.content
    client.delete(f"{AUTH}/session")
    response = client.post(
        f"{AUTH}/login",
        data={"email": user.email, "password": "NewSafePass_2026!"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content


def test_display_name_is_case_insensitively_unique():
    client = Client()
    assert signup(client).status_code == 401
    response = signup(Client(), email="other@example.test", display_name="omarmusic")
    assert response.status_code == 400
    assert "display_name" in str(response.content)


def test_signup_accepts_csrf_from_local_web_origin():
    client = Client(enforce_csrf_checks=True)
    csrf_response = client.get("/api/csrf")

    response = client.post(
        f"{AUTH}/signup",
        data={
            "email": "browser@example.test",
            "password": "SafePass_2026!",
            "first_name": "Omar",
            "last_name": "Mussa",
            "display_name": "BrowserUser",
        },
        content_type="application/json",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_X_CSRFTOKEN=csrf_response.json()["csrfToken"],
    )

    assert response.status_code == 401, response.content
    assert get_user_model().objects.filter(email="browser@example.test").exists()


def test_me_only_returns_the_authenticated_users_profile():
    user_model = get_user_model()
    user_a = user_model.objects.create_user(
        email="a@example.test",
        password="SafePass_2026!",
        first_name="User",
        last_name="A",
        display_name="UserA",
    )
    user_model.objects.create_user(
        email="b@example.test",
        password="SafePass_2026!",
        first_name="User",
        last_name="B",
        display_name="UserB",
    )
    client = Client()
    client.force_login(user_a)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["email"] == "a@example.test"
    assert response.json()["language"] == "en"
    assert "b@example.test" not in response.content.decode()


def test_profile_language_cannot_be_changed_from_english():
    user = get_user_model().objects.create_user(
        email="language@example.test",
        password="SafePass_2026!",
        first_name="English",
        last_name="Only",
        display_name="EnglishOnly",
    )
    client = Client()
    client.force_login(user)

    response = client.patch(
        "/api/me",
        data={"language": "sw"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert (
        response.json()["error"]["message"]
        == "Please check the information you entered."
    )
    user.refresh_from_db()
    assert user.language == "en"


def test_delete_account_anonymizes_and_keeps_wallet():
    client = Client()
    assert signup(client).status_code == 401
    user = get_user_model().objects.get(email="omar@example.test")
    job = SongJob.objects.create(
        user=user,
        title="Private song title",
        idea="Private song idea",
        lyrics="Private lyrics",
        price_tzs=1000,
    )
    SongVersion.objects.create(
        job=job,
        index=0,
        status=SongVersion.Status.READY,
        storage_key=f"songs/{user.pk}/{job.pk}/0.mp3",
    )
    staff_user = get_user_model().objects.create_superuser(
        email="billing-admin@example.test",
        password="SafePass_2026!",
        first_name="Billing",
        last_name="Admin",
        display_name="BillingAdmin",
    )
    wallet = Wallet.objects.get(user=user)
    adjust(wallet, 1000, "Test funding for account deletion", staff_user)
    charge_song(user, job, 1000)
    LyricsRequest.objects.create(user=user, prompt="Private lyrics prompt")
    SupportMessage.objects.create(
        user=user,
        name="Omar",
        email=user.email,
        message="Please help with my account.",
    )
    client.force_login(user)

    with patch("apps.accounts.services.default_storage.delete") as delete_file:
        response = client.post(
            "/api/me/delete",
            data={"password": "SafePass_2026!"},
            content_type="application/json",
        )

    assert response.status_code == 204
    user.refresh_from_db()
    assert not user.is_active
    assert user.deleted_at is not None
    assert user.display_name == f"deleted-{user.pk.hex[:22]}"
    assert len(user.display_name) == 30
    assert user.phone_last_used is None
    assert not EmailAddress.objects.filter(user=user).exists()
    assert Wallet.objects.filter(user=user, balance_tzs=0).exists()
    job.refresh_from_db()
    assert job.title == job.idea == job.lyrics == ""
    assert job.deleted_at is not None
    assert not SongVersion.objects.filter(job=job).exists()
    assert not LyricsRequest.objects.filter(user=user).exists()
    assert not SupportMessage.objects.filter(user=user).exists()
    assert Wallet.objects.get(user=user).balance_tzs == 0
    assert LedgerEntry.objects.filter(song_job=job).count() == 1
    fail_job(job.pk, reason="late_provider_failure")
    finalize_job(job.pk)
    assert Wallet.objects.get(user=user).balance_tzs == 0
    assert LedgerEntry.objects.filter(song_job=job).count() == 1
    delete_file.assert_called_once_with(f"songs/{user.pk}/{job.pk}/0.mp3")
    assert dispatch_jobs() == 0


def test_delete_account_with_wrong_password_keeps_private_data():
    client = Client()
    assert signup(client).status_code == 401
    user = get_user_model().objects.get(email="omar@example.test")
    job = SongJob.objects.create(
        user=user,
        title="Private song title",
        idea="Private song idea",
        lyrics="Private lyrics",
        price_tzs=1000,
    )
    SongVersion.objects.create(
        job=job,
        index=0,
        storage_key=f"songs/{user.pk}/{job.pk}/0.mp3",
    )
    client.force_login(user)

    response = client.post(
        "/api/me/delete",
        data={"password": "incorrect"},
        content_type="application/json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    job.refresh_from_db()
    assert user.is_active
    assert user.deleted_at is None
    assert job.title == "Private song title"


def test_delete_account_storage_failure_leaves_account_and_songs_intact():
    client = Client()
    assert signup(client).status_code == 401
    user = get_user_model().objects.get(email="omar@example.test")
    job = SongJob.objects.create(
        user=user,
        title="Private song title",
        idea="Private song idea",
        lyrics="Private lyrics",
        price_tzs=1000,
    )
    SongVersion.objects.create(
        job=job,
        index=0,
        storage_key=f"songs/{user.pk}/{job.pk}/0.mp3",
    )
    client.force_login(user)

    with patch(
        "apps.accounts.services.default_storage.delete",
        side_effect=OSError("storage unavailable"),
    ):
        response = client.post(
            "/api/me/delete",
            data={"password": "SafePass_2026!"},
            content_type="application/json",
        )

    assert response.status_code == 503
    user.refresh_from_db()
    job.refresh_from_db()
    assert user.is_active
    assert user.deleted_at is None
    assert job.title == "Private song title"
