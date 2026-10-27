from unittest.mock import patch

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
