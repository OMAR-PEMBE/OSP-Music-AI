from unittest.mock import patch

import pytest
from django.test import Client


def test_health_checks_database_and_redis():
    client = Client()
    with (
        patch("apps.core.views.connection.cursor") as cursor,
        patch("apps.core.views.Redis.from_url") as redis,
    ):
        cursor.return_value.__enter__.return_value.execute.return_value = None
        redis.return_value.ping.return_value = True
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"db": "ok", "redis": "ok"}
    cursor.assert_called_once()
    redis.return_value.ping.assert_called_once()


@pytest.mark.django_db
def test_public_config_returns_app_settings_for_the_web_app():
    response = Client().get("/api/config")

    assert response.status_code == 200
    assert response.json()["song_price_tzs"] == 1000
    assert response.json()["topup_presets_tzs"] == [1000, 3000, 5000, 10000]
    assert "other" in response.json()["genres"]


def test_csrf_endpoint_sets_cookie_and_returns_a_token():
    response = Client(enforce_csrf_checks=True).get("/api/csrf")

    assert response.status_code == 200
    assert response.json()["csrfToken"]
    assert "csrftoken" in response.cookies
