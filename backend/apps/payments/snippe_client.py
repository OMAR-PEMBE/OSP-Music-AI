"""Small stdlib-only HTTP client for Snippe's payment API."""

import json
import urllib.error
import urllib.request
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.utils import timezone


class SnippeError(Exception):
    """A network or provider error that prevented a trustworthy response."""


class SnippeNetworkError(SnippeError):
    """A transport failure that is safe to retry with the same idempotency key."""


class SnippeClient:
    def __init__(self, *, base_url=None, api_key=None, timeout=15):
        self.base_url = (base_url or settings.SNIPPE_BASE_URL).rstrip("/")
        self.api_key = settings.SNIPPE_API_KEY if api_key is None else api_key
        self.timeout = timeout

    def _request(self, method, path, *, body=None, idempotency_key=None):
        if not self.api_key:
            raise SnippeError("Snippe API key is not configured.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        data = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise SnippeError(f"Snippe returned HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SnippeNetworkError("Snippe network request failed.") from exc
        except ValueError as exc:
            raise SnippeError("Snippe returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise SnippeError("Snippe returned an invalid response.")
        return payload

    def create_payment(self, payment, *, attempts=3):
        user = payment.user
        body = {
            "payment_type": "mobile",
            "details": {"amount": payment.amount_tzs, "currency": "TZS"},
            "phone_number": payment.phone,
            "customer": {
                "firstname": user.first_name,
                "lastname": user.last_name,
                "email": user.email,
            },
            "webhook_url": f"{settings.PUBLIC_BASE_URL.rstrip('/')}/webhooks/snippe",
            "metadata": {"payment_id": str(payment.pk)},
        }
        last_error = None
        for _ in range(attempts):
            try:
                return self._request(
                    "POST",
                    "/v1/payments",
                    body=body,
                    idempotency_key=payment.short_id,
                )
            except SnippeNetworkError as exc:
                last_error = exc
        if last_error is None:
            raise SnippeError("Snippe request failed.")
        raise last_error or SnippeError("Snippe request failed.")

    def get_payment(self, reference):
        return self._request("GET", f"/v1/payments/{quote(reference, safe='')}")


class FakeSnippeClient:
    """Local-only payment simulator; it never makes network requests."""

    def create_payment(self, payment):
        return {
            "data": {
                "reference": f"local-demo-{payment.pk}",
                "expires_at": (timezone.now() + timedelta(hours=4)).isoformat(),
            }
        }

    def get_payment(self, reference):
        from .models import Payment

        payment = Payment.objects.get(snippe_reference=reference)
        return {
            "data": {
                "status": "completed",
                "amount": {"value": payment.amount_tzs, "currency": "TZS"},
                "completed_at": timezone.now().isoformat(),
                "channel": {"provider": "local_demo"},
                "settlement": {"fees": {"value": 0}},
            }
        }
