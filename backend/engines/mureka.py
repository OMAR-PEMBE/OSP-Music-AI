import json
import logging
import time
import urllib.error
import urllib.request
from urllib.parse import quote

from django.conf import settings

from .base import EngineError, LyricsResult, SongChoice, SongRequest, SongStatus

logger = logging.getLogger(__name__)
_capacity_value = None
_capacity_expires_at = 0.0
_account_balance_usd_cents = None


class MurekaError(EngineError):
    pass


class MurekaClient:
    def __init__(self, *, api_key=None, base_url=None, timeout=30):
        self.api_key = settings.MUREKA_API_KEY if api_key is None else api_key
        self.base_url = (base_url or settings.MUREKA_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.last_trace_id = None

    def request(self, method, path, *, body=None):
        if not self.api_key:
            raise MurekaError("Mureka API key is not configured.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        encoded_body = None
        if body is not None:
            encoded_body = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=encoded_body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.last_trace_id = (
                    response.headers.get("trace_id")
                    or response.headers.get("x-trace-id")
                    or (data.get("trace_id") if isinstance(data, dict) else None)
                )
        except urllib.error.HTTPError as exc:
            trace_id = exc.headers.get("trace_id") or exc.headers.get("x-trace-id")
            try:
                error_body = json.loads(exc.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_body = {}
            if isinstance(error_body, dict):
                trace_id = trace_id or error_body.get("trace_id")
            self.last_trace_id = trace_id
            raise MurekaError(
                f"Mureka returned HTTP {exc.code}.",
                status_code=exc.code,
                trace_id=trace_id,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MurekaError("Mureka network request failed.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MurekaError("Mureka returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise MurekaError("Mureka returned an invalid response.")
        return data


class MurekaEngine:
    name = "mureka"

    def __init__(self, client=None):
        self.client = client or MurekaClient()

    @property
    def last_trace_id(self):
        return self.client.last_trace_id

    def generate_lyrics(self, prompt: str) -> LyricsResult:
        data = self.client.request(
            "POST", "/v1/lyrics/generate", body={"prompt": prompt}
        )
        title, lyrics = data.get("title"), data.get("lyrics")
        if not isinstance(title, str) or not isinstance(lyrics, str):
            raise MurekaError(
                "Mureka returned incomplete lyrics.", trace_id=self.last_trace_id
            )
        return LyricsResult(title=title[:120], lyrics=lyrics[:5000])

    def submit_song(self, request: SongRequest) -> str:
        body = {
            "lyrics": request.lyrics[:5000],
            "model": request.model,
            "prompt": request.prompt[:1024],
            "n": 2,
            "stream": True,
        }
        if request.voice in {"male", "female"}:
            body["gender"] = request.voice
        data = self.client.request("POST", "/v1/song/generate", body=body)
        task_id = data.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise MurekaError(
                "Mureka response omitted task id.", trace_id=self.last_trace_id
            )
        return task_id

    def get_status(self, task_id: str, *, poll_attempt: int = 0) -> SongStatus:
        del poll_attempt
        data = self.client.request("GET", f"/v1/song/query/{quote(task_id, safe='')}")
        provider_status = str(data.get("status", "unknown"))
        choices = []
        for fallback_index, item in enumerate(data.get("choices") or []):
            if not isinstance(item, dict):
                continue
            index = item.get("index", fallback_index)
            if type(index) is not int or index not in {0, 1}:
                continue
            duration = item.get("duration")
            choices.append(
                SongChoice(
                    index=index,
                    provider_song_id=_optional_string(item.get("id")),
                    url=_optional_string(item.get("url")),
                    stream_url=_optional_string(item.get("stream_url")),
                    duration_ms=(
                        duration if type(duration) is int and duration >= 0 else None
                    ),
                )
            )
        normalized = {
            "preparing": "running",
            "queued": "running",
            "running": "running",
            "streaming": "streaming",
            "succeeded": "succeeded",
            "failed": "failed",
            "timeouted": "timeouted",
            "cancelled": "cancelled",
        }.get(provider_status, "unknown")
        return SongStatus(
            status=normalized,
            provider_status=provider_status[:20],
            failed_reason=_optional_string(data.get("failed_reason")),
            choices=choices,
        )

    def get_capacity(self) -> int:
        global _capacity_value, _capacity_expires_at
        if _capacity_value and time.monotonic() < _capacity_expires_at:
            return _capacity_value
        try:
            account = self.refresh_account()
            limit = account["concurrent_request_limit"]
        except MurekaError as exc:
            logger.warning(
                "mureka_capacity_lookup_failed trace_id=%s status=%s",
                exc.trace_id,
                exc.status_code,
            )
            limit = 1
        _capacity_value = limit
        _capacity_expires_at = time.monotonic() + 600
        return limit

    def refresh_account(self):
        global _capacity_value, _capacity_expires_at, _account_balance_usd_cents
        data = self.client.request("GET", "/v1/account/billing")
        limit = data.get("concurrent_request_limit")
        if type(limit) is not int or limit < 1:
            raise MurekaError(
                "Mureka returned an invalid capacity limit.",
                trace_id=self.last_trace_id,
            )
        balance = data.get("balance")
        if type(balance) is str and balance.isdecimal():
            balance = int(balance)
        if type(balance) is not int or balance < 0:
            balance = None
        _capacity_value = limit
        _capacity_expires_at = time.monotonic() + 600
        _account_balance_usd_cents = balance
        return {
            "concurrent_request_limit": limit,
            "balance_usd_cents": balance,
        }


def _optional_string(value):
    return value if isinstance(value, str) and value else None
