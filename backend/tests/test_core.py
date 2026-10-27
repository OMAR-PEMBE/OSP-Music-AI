import smtplib
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, override_settings

from apps.core.models import AppSettings, SupportMessage

pytestmark = pytest.mark.django_db

SUPPORT_URL = "/api/support"
SUPPORT_PAYLOAD = {
    "name": "Amina",
    "email": "amina@example.test",
    "message": "I need help with my account.",
}


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.test",
)
def test_support_message_emails_owner_and_links_authenticated_user():
    app_settings = AppSettings.objects.create(support_email="owner@example.test")
    user = get_user_model().objects.create_user(
        email="amina@example.test",
        password="SafePass_2026!",
        first_name="Amina",
        last_name="User",
        display_name="AminaUser",
    )
    client = Client()
    client.force_login(user)

    response = client.post(
        SUPPORT_URL, data=SUPPORT_PAYLOAD, content_type="application/json"
    )

    assert response.status_code == 201
    message = SupportMessage.objects.get(pk=response.json()["id"])
    assert message.user == user
    assert message.name == SUPPORT_PAYLOAD["name"]
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [app_settings.support_email]
    assert mail.outbox[0].reply_to == [SUPPORT_PAYLOAD["email"]]
    assert mail.outbox[0].body == SUPPORT_PAYLOAD["message"]


def test_support_message_rejects_short_content_and_requires_configuration():
    client = Client()
    response = client.post(
        SUPPORT_URL,
        data={**SUPPORT_PAYLOAD, "message": "short"},
        content_type="application/json",
    )
    assert response.status_code == 400

    response = client.post(
        SUPPORT_URL,
        data=SUPPORT_PAYLOAD,
        content_type="application/json",
    )
    assert response.status_code == 503
    assert SupportMessage.objects.count() == 0


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.test",
)
def test_anonymous_support_message_is_accepted():
    AppSettings.objects.create(support_email="owner@example.test")

    response = Client().post(
        SUPPORT_URL,
        data=SUPPORT_PAYLOAD,
        content_type="application/json",
    )

    assert response.status_code == 201
    assert SupportMessage.objects.get(pk=response.json()["id"]).user is None


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.test",
)
def test_support_email_failure_returns_error_and_keeps_message_for_staff():
    AppSettings.objects.create(support_email="owner@example.test")
    with patch(
        "apps.core.views.EmailMessage.send",
        side_effect=smtplib.SMTPException("mail server unavailable"),
    ):
        response = Client().post(
            SUPPORT_URL,
            data=SUPPORT_PAYLOAD,
            content_type="application/json",
        )

    assert response.status_code == 503
    assert SupportMessage.objects.filter(email=SUPPORT_PAYLOAD["email"]).exists()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.test",
)
def test_support_message_is_limited_to_three_per_ip_per_hour():
    AppSettings.objects.create(support_email="owner@example.test")
    client = Client()

    responses = [
        client.post(SUPPORT_URL, data=SUPPORT_PAYLOAD, content_type="application/json")
        for _ in range(4)
    ]

    assert [response.status_code for response in responses] == [
        201,
        201,
        201,
        429,
    ]
    assert SupportMessage.objects.count() == 3
