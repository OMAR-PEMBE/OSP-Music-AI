from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import timezone

from .base import EngineUnavailable

CAPACITY_FALLBACK_DELAY = timedelta(minutes=2)


def estimate_request_cost_usd_cents(app_settings, engine, *, needs_lyrics=True):
    if engine == "suno":
        song_cost = app_settings.suno_cost_per_version_usd_cents
        if song_cost is None:
            return None
    else:
        song_cost = app_settings.cost_per_version_usd_cents
    total = song_cost * 2
    if needs_lyrics:
        total += app_settings.cost_per_lyrics_usd_cents
    return int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _within_margin(app_settings, engine):
    if engine == "suno":
        cost_per_version = app_settings.suno_cost_per_version_usd_cents
    else:
        cost_per_version = app_settings.cost_per_version_usd_cents
    if cost_per_version is None:
        return False
    total_cost_cents = cost_per_version * 2 + app_settings.cost_per_lyrics_usd_cents
    return total_cost_cents * app_settings.usd_to_tzs <= Decimal(
        app_settings.song_price_tzs * 60
    )


def _is_available(app_settings, engine):
    if not _within_margin(app_settings, engine):
        return False
    if engine == "suno":
        # SUNO.md §3 has no official request/status contract. Only FakeEngine
        # can exercise this engine name until Omar supplies those API details.
        return bool(settings.SUNO_API_KEY) and settings.MUSIC_ENGINE == "fake"
    if settings.MUSIC_ENGINE != "fake" and not settings.MUREKA_API_KEY:
        return False
    request_cost = estimate_request_cost_usd_cents(app_settings, "mureka")
    balance = app_settings.mureka_balance_usd_cents
    return balance is None or balance >= request_cost


def _make_engine(engine_name):
    if settings.MUSIC_ENGINE == "fake":
        from .fake import FakeEngine

        return FakeEngine(engine_name=engine_name)
    if engine_name == "mureka":
        from .mureka import MurekaEngine

        return MurekaEngine()
    from .suno import SunoEngine

    return SunoEngine()


def get_engine_for_new_job(
    preferred_engine=None,
    *,
    app_settings=None,
    capacity_error_since=None,
):
    if app_settings is None:
        from apps.core.models import get_app_settings

        app_settings = get_app_settings()
    if not app_settings.generation_enabled:
        raise EngineUnavailable("Music generation is paused.")

    preferred = preferred_engine or app_settings.active_engine
    capacity_timed_out = (
        capacity_error_since is not None
        and timezone.now() - capacity_error_since >= CAPACITY_FALLBACK_DELAY
    )
    if not capacity_timed_out and _is_available(app_settings, preferred):
        return _make_engine(preferred)

    fallback = app_settings.fallback_engine
    if (
        fallback != "none"
        and fallback != preferred
        and _is_available(app_settings, fallback)
    ):
        return _make_engine(fallback)
    if capacity_timed_out:
        raise EngineUnavailable("Engine capacity remains unavailable.")
    raise EngineUnavailable("No configured music engine is available.")


def get_engine_for_job(job):
    if settings.MUSIC_ENGINE == "fake":
        from .fake import FakeEngine

        return FakeEngine(engine_name=job.engine)
    if job.engine == "mureka":
        from .mureka import MurekaEngine

        return MurekaEngine()
    if job.engine == "suno":
        from .suno import SunoEngine

        return SunoEngine()
    raise EngineUnavailable(f"No engine registered for {job.engine}.")


def get_engine_for_lyrics():
    if settings.MUSIC_ENGINE == "fake":
        from .fake import FakeEngine

        return FakeEngine()
    from .mureka import MurekaEngine

    return MurekaEngine()
