import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.message import BadHeaderError
from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from redis import Redis
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SupportMessage, get_app_settings
from .serializers import SupportMessageSerializer
from .throttles import SupportIPRateThrottle

logger = logging.getLogger(__name__)


class SupportUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "support_unavailable"


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


class SupportView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SupportIPRateThrottle]

    def post(self, request):
        serializer = SupportMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        app_settings = get_app_settings()
        from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        if not app_settings.support_email or not from_email:
            raise SupportUnavailable(
                detail="Support contact is not configured.",
                code="support_unavailable",
            )

        message = SupportMessage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            **serializer.validated_data,
        )
        email = EmailMessage(
            subject=f"OSP Music AI support message #{message.pk}",
            body=message.message,
            from_email=from_email,
            to=[app_settings.support_email],
            reply_to=[message.email],
        )
        try:
            email.send(fail_silently=False)
        except (BadHeaderError, OSError, smtplib.SMTPException):
            logger.exception("support_email_delivery_failed message_id=%s", message.pk)
            raise SupportUnavailable(
                detail="Support message could not be delivered. Please try again.",
                code="support_delivery_failed",
            )

        return Response(
            {"id": message.pk},
            status=status.HTTP_201_CREATED,
        )


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({"csrfToken": get_token(request)})
