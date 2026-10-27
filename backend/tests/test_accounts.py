import re

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client

from apps.wallet.models import Wallet

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
    assert "b@example.test" not in response.content.decode()


def test_delete_account_anonymizes_and_keeps_wallet():
    client = Client()
    assert signup(client).status_code == 401
    user = get_user_model().objects.get(email="omar@example.test")
    client.force_login(user)

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
