from django.conf import settings
from django.db import connection
from django.db.utils import DatabaseError
from redis import Redis
from redis.exceptions import RedisError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    status = {"db": "ok", "redis": "ok"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        status["db"] = "error"

    try:
        Redis.from_url(settings.REDIS_URL).ping()
    except RedisError:
        status["redis"] = "error"

    http_status = 200 if all(value == "ok" for value in status.values()) else 503
    return Response(status, status=http_status)
