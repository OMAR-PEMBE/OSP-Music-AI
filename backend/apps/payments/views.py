import hashlib
import hmac
import json
import time
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallet.permissions import IsEmailVerified

from .models import Payment, WebhookEvent
from .serializers import TopupCreateSerializer, TopupPaymentSerializer
from .services import PaymentProviderError, create_payment
from .tasks import process_snippe_event


class PaymentRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Top-up limit reached."
    default_code = "rate_limited"


class PaymentProviderUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Payment provider unavailable."
    default_code = "payment_provider_error"


class TopupsView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def post(self, request):
        serializer = TopupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = timezone.now()
        user_payments = Payment.objects.filter(user_id=request.user.pk)
        pending_count = user_payments.filter(status=Payment.Status.PENDING).count()
        recent_count = user_payments.filter(
            created_at__gte=now - timedelta(hours=1)
        ).count()
        if pending_count >= 3 or recent_count >= 10:
            raise PaymentRateLimited()
        try:
            payment = create_payment(request.user, **serializer.validated_data)
        except PaymentProviderError as exc:
            raise PaymentProviderUnavailable() from exc
        return Response(
            TopupPaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class TopupDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(pk=payment_id, user_id=request.user.pk)
        except (Payment.DoesNotExist, ValueError):
            raise NotFound()
        return Response(TopupPaymentSerializer(payment).data)


class SnippeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_body = request._request.body
        timestamp = request.headers.get("X-Webhook-Timestamp", "")
        signature = request.headers.get("X-Webhook-Signature", "")
        try:
            timestamp_int = int(timestamp)
        except (TypeError, ValueError):
            timestamp_int = 0
        fresh = timestamp_int > 0 and abs(time.time() - timestamp_int) <= 300
        message = timestamp.encode("ascii", errors="ignore") + b"." + raw_body
        expected = hmac.new(
            settings.SNIPPE_WEBHOOK_SECRET.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()
        signature_valid = (
            bool(settings.SNIPPE_WEBHOOK_SECRET)
            and fresh
            and hmac.compare_digest(expected, signature)
        )
        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                {"detail": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(payload, dict):
            return Response(
                {"detail": "Invalid event."}, status=status.HTTP_400_BAD_REQUEST
            )
        event_id = payload.get("id")
        event_type = payload.get("type", "")
        data = payload.get("data") or {}
        reference = data.get("reference", "") if isinstance(data, dict) else ""
        if not event_id or not event_type or not reference:
            return Response(
                {"detail": "Invalid event."}, status=status.HTTP_400_BAD_REQUEST
            )
        defaults = {
            "event_type": str(event_type)[:40],
            "reference": str(reference)[:64],
            "payload": payload,
            "signature_valid": signature_valid,
        }
        if not signature_valid:
            WebhookEvent.objects.get_or_create(
                event_id=str(event_id)[:64], defaults=defaults
            )
            return Response(
                {"detail": "Invalid signature or stale timestamp."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event, created = WebhookEvent.objects.get_or_create(
            event_id=str(event_id)[:64], defaults=defaults
        )
        if not created and not event.signature_valid:
            for field, value in defaults.items():
                setattr(event, field, value)
            event.processed_at = None
            event.save()
        elif not created:
            return Response(status=status.HTTP_200_OK)
        process_snippe_event.delay(str(event.pk))
        return Response(status=status.HTTP_200_OK)


snippe_webhook_view = csrf_exempt(SnippeWebhookView.as_view())
