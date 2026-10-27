from django.conf import settings
from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from redis import Redis
from redis.exceptions import RedisError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import get_app_settings


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


class ConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        del request
        app_settings = get_app_settings()
        return Response(
            {
                "song_price_tzs": app_settings.song_price_tzs,
                "min_topup_tzs": app_settings.min_topup_tzs,
                "max_topup_tzs": app_settings.max_topup_tzs,
                "topup_presets_tzs": [1000, 3000, 5000, 10000],
                "generation_enabled": app_settings.generation_enabled,
                "payment_demo": settings.DEBUG and settings.SNIPPE_FAKE_MODE,
                "lyrics_daily_limit": app_settings.lyrics_daily_limit,
                "support_whatsapp": app_settings.support_whatsapp,
                "genres": [
                    "bongo_flava",
                    "rnb",
                    "afrobeats",
                    "amapiano",
                    "gospel",
                    "hiphop",
                    "other",
                ],
            }
        )


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({"csrfToken": get_token(request)})
