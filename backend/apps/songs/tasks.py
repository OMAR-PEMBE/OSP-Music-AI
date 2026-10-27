import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from engines.base import EngineError, EngineUnavailable, SongRequest
from engines.factory import get_engine_for_job, get_engine_for_new_job
from engines.mureka import MurekaError
from engines.router import estimate_request_cost_usd_cents

from .models import SongJob, SongVersion
from .services import build_lyrics_prompt, build_style_prompt, fail_job, finalize_job
from .storage import store_audio_version

logger = logging.getLogger(__name__)
ACTIVE_STATUSES = [
    SongJob.Status.SUBMITTING,
    SongJob.Status.RUNNING,
    SongJob.Status.STREAMING,
]


def _claim_queued_job(job_id, engine_name):
    with transaction.atomic():
        job = (
            SongJob.objects.select_for_update(skip_locked=True)
            .filter(pk=job_id, status=SongJob.Status.QUEUED)
            .first()
        )
        if job is None:
            return None
        if job.engine != engine_name:
            from apps.core.models import get_app_settings

            job.engine = engine_name
            job.est_cost_usd_cents = estimate_request_cost_usd_cents(
                get_app_settings(), engine_name, needs_lyrics=not bool(job.lyrics)
            )
            job.capacity_error_since = None
        job.status = SongJob.Status.SUBMITTING
        job.failure_reason = None
        job.save(
            update_fields=[
                "engine",
                "est_cost_usd_cents",
                "capacity_error_since",
                "status",
                "failure_reason",
                "updated_at",
            ]
        )
        return job


def _submit_job(job_id, engine):
    job = SongJob.objects.select_related("user").get(pk=job_id)
    if not job.lyrics:
        prompt = build_lyrics_prompt(
            genre=job.genre,
            language=job.language,
            idea=job.idea,
            genre_other=job.genre_other,
        )
        generated = engine.generate_lyrics(prompt)
        job.lyrics = generated.lyrics[:5000]
        job.lyrics_source = SongJob.LyricsSource.GENERATED
        job.title = generated.title[:120] or job.title
        job.save(update_fields=["lyrics", "lyrics_source", "title", "updated_at"])

    request = SongRequest(
        job_id=str(job.pk),
        idea=job.idea,
        lyrics=job.lyrics,
        model=job.model,
        prompt=build_style_prompt(
            genre=job.genre,
            language=job.language,
            voice=job.voice,
            idea=job.idea,
            genre_other=job.genre_other,
        ),
        voice=job.voice,
    )
    task_id = engine.submit_song(request)
    if not isinstance(task_id, str) or not task_id or len(task_id) > 64:
        raise EngineError("Engine response omitted a valid task id.")
    trace_id = getattr(engine, "last_trace_id", None)
    SongJob.objects.filter(pk=job_id, status=SongJob.Status.SUBMITTING).update(
        provider_task_id=task_id,
        provider_trace_id=trace_id,
        provider_status="queued",
        submitted_at=timezone.now(),
        status=SongJob.Status.RUNNING,
    )
    logger.info(
        "song_submitted engine=%s job_id=%s provider_task_id=%s provider_trace_id=%s",
        job.engine,
        job_id,
        task_id,
        trace_id,
    )
    return True


@shared_task(name="apps.songs.dispatch_jobs")
def dispatch_jobs():
    from apps.core.models import get_app_settings

    app_settings = get_app_settings()
    if not app_settings.generation_enabled:
        return 0
    queued_jobs = list(
        SongJob.objects.filter(status=SongJob.Status.QUEUED).order_by(
            "created_at", "id"
        )[:100]
    )
    active_counts = {
        engine_name: SongJob.objects.filter(
            engine=engine_name, status__in=ACTIVE_STATUSES
        ).count()
        for engine_name in SongJob.Engine.values
    }
    capacities = {}
    submitted = 0
    for queued_job in queued_jobs:
        try:
            engine = get_engine_for_new_job(
                preferred_engine=queued_job.engine,
                app_settings=app_settings,
                capacity_error_since=queued_job.capacity_error_since,
            )
        except EngineUnavailable as exc:
            logger.info(
                "song_job_waiting_for_engine job_id=%s reason=%s", queued_job.pk, exc
            )
            continue
        engine_name = engine.name
        if engine_name not in capacities:
            capacities[engine_name] = max(engine.get_capacity(), 0)
        if active_counts[engine_name] >= capacities[engine_name]:
            continue
        job = _claim_queued_job(queued_job.pk, engine_name)
        if job is None:
            continue
        try:
            if _submit_job(job.pk, engine):
                submitted += 1
                active_counts[engine_name] += 1
        except EngineError as exc:
            if exc.status_code == 429:
                SongJob.objects.filter(pk=job.pk).update(
                    status=SongJob.Status.QUEUED,
                    provider_status="capacity",
                    provider_trace_id=exc.trace_id,
                    capacity_error_since=job.capacity_error_since or timezone.now(),
                    updated_at=timezone.now(),
                )
                logger.info(
                    "song_submission_deferred engine=%s job_id=%s provider_trace_id=%s",
                    engine_name,
                    job.pk,
                    exc.trace_id,
                )
                continue
            if isinstance(exc, EngineUnavailable):
                SongJob.objects.filter(pk=job.pk).update(
                    status=SongJob.Status.QUEUED,
                    updated_at=timezone.now(),
                )
                continue
            reason = (
                "provider_rejected"
                if exc.status_code is not None and 400 <= exc.status_code < 500
                else "submit_uncertain"
            )
            logger.error(
                "song_submission_failed engine=%s job_id=%s reason=%s provider_trace_id=%s",
                engine_name,
                job.pk,
                reason,
                exc.trace_id,
            )
            fail_job(job.pk, reason=reason, trace_id=exc.trace_id)
        except Exception:
            logger.exception("song_submission_uncertain job_id=%s", job.pk)
            fail_job(job.pk, reason="submit_uncertain")
    return submitted


def _poll_one(job):
    if job.submitted_at and timezone.now() - job.submitted_at > timedelta(
        seconds=settings.MUREKA_JOB_TIMEOUT_SECONDS
    ):
        fail_job(
            job.pk,
            reason="timeout_ours",
            provider_status=job.provider_status,
        )
        return
    engine = get_engine_for_job(job)
    poll_attempt = job.poll_attempts
    SongJob.objects.filter(pk=job.pk).update(poll_attempts=F("poll_attempts") + 1)
    try:
        result = engine.get_status(job.provider_task_id, poll_attempt=poll_attempt)
    except EngineError as exc:
        if exc.trace_id:
            SongJob.objects.filter(pk=job.pk).update(provider_trace_id=exc.trace_id)
        logger.warning(
            "song_poll_failed engine=%s job_id=%s provider_task_id=%s provider_trace_id=%s",
            job.engine,
            job.pk,
            job.provider_task_id,
            exc.trace_id,
        )
        return
    SongJob.objects.filter(pk=job.pk).update(
        provider_status=result.provider_status[:20],
        provider_trace_id=getattr(engine, "last_trace_id", None)
        or job.provider_trace_id,
        updated_at=timezone.now(),
    )

    if result.status == "streaming":
        with transaction.atomic():
            current = SongJob.objects.select_for_update().get(pk=job.pk)
            if current.status not in {
                SongJob.Status.READY,
                SongJob.Status.PARTIAL,
                SongJob.Status.FAILED,
            }:
                current.status = SongJob.Status.STREAMING
                current.save(update_fields=["status", "updated_at"])
                for choice in result.choices:
                    if not choice.stream_url:
                        continue
                    SongVersion.objects.filter(job=current, index=choice.index).update(
                        status=SongVersion.Status.STREAMING,
                        stream_url=choice.stream_url,
                        provider_song_id=choice.provider_song_id,
                    )
        return

    if result.status == "succeeded":
        choices = {choice.index: choice for choice in result.choices}
        for index in range(job.versions_requested):
            choice = choices.get(index)
            version = SongVersion.objects.get(job_id=job.pk, index=index)
            if not choice or not choice.url:
                if version.status != SongVersion.Status.READY:
                    SongVersion.objects.filter(pk=version.pk).update(
                        status=SongVersion.Status.FAILED,
                        provider_song_id=choice.provider_song_id if choice else None,
                    )
                continue
            if version.status != SongVersion.Status.READY:
                store_version.delay(str(job.pk), index, choice.url, choice.duration_ms)
        finalize_job(job.pk)
        return

    if result.status in {"failed", "timeouted", "cancelled"}:
        fail_job(
            job.pk,
            reason=(result.failed_reason or result.status)[:255],
            provider_status=result.provider_status,
            trace_id=getattr(engine, "last_trace_id", None),
        )
        return

    if result.status == "running" and job.status == SongJob.Status.SUBMITTING:
        SongJob.objects.filter(pk=job.pk).update(
            status=SongJob.Status.RUNNING,
            updated_at=timezone.now(),
        )


@shared_task(name="apps.songs.poll_jobs")
def poll_jobs():
    jobs = list(
        SongJob.objects.filter(
            status__in=[SongJob.Status.RUNNING, SongJob.Status.STREAMING],
        ).order_by("submitted_at", "created_at")[:50]
    )
    for job in jobs:
        try:
            _poll_one(job)
        except Exception:
            logger.exception("song_poll_processing_failed job_id=%s", job.pk)
    return len(jobs)


@shared_task(name="apps.songs.refresh_mureka_account")
def refresh_mureka_account():
    if settings.MUSIC_ENGINE == "fake" or not settings.MUREKA_API_KEY:
        return None
    from apps.core.models import get_app_settings
    from engines.mureka import MurekaEngine

    engine = MurekaEngine()
    try:
        account = engine.refresh_account()
    except MurekaError as exc:
        logger.warning(
            "mureka_capacity_lookup_failed trace_id=%s status=%s",
            exc.trace_id,
            exc.status_code,
        )
        return None
    balance = account["balance_usd_cents"]
    if balance is None:
        logger.warning(
            "mureka_balance_missing trace_id=%s",
            engine.last_trace_id,
        )
        return account["concurrent_request_limit"]

    app_settings = get_app_settings()
    app_settings.mureka_balance_usd_cents = balance
    app_settings.save(update_fields=["mureka_balance_usd_cents"])
    if balance < app_settings.mureka_low_balance_usd * 100:
        logger.warning(
            "mureka_low_balance balance_usd_cents=%s trace_id=%s",
            balance,
            engine.last_trace_id,
        )
    request_cost_cents = (
        app_settings.cost_per_version_usd_cents * 2
        + app_settings.cost_per_lyrics_usd_cents
    )
    if balance < request_cost_cents:
        logger.warning(
            "mureka_unavailable_low_balance balance_usd_cents=%s trace_id=%s",
            balance,
            engine.last_trace_id,
        )
    return account["concurrent_request_limit"]


@shared_task(bind=True, max_retries=5, name="apps.songs.store_version")
def store_version(self, job_id, index, url, duration_ms=None):
    try:
        job = SongJob.objects.select_related("user").get(pk=job_id)
        version = SongVersion.objects.get(job=job, index=index)
        if version.status == SongVersion.Status.READY:
            return
        if not job.deleted_at:
            version = store_audio_version(job, version, url, duration_ms)
        with transaction.atomic():
            locked_job = SongJob.objects.select_for_update().get(pk=job_id)
            locked_version = SongVersion.objects.select_for_update().get(pk=version.pk)
            if locked_version.status == SongVersion.Status.READY:
                return
            locked_version.status = SongVersion.Status.READY
            if locked_job.deleted_at:
                if version.storage_key:
                    default_storage.delete(version.storage_key)
                locked_version.storage_key = None
                locked_version.size_bytes = None
            else:
                locked_version.storage_key = version.storage_key
                locked_version.size_bytes = version.size_bytes
            locked_version.duration_ms = duration_ms
            locked_version.save(
                update_fields=[
                    "status",
                    "storage_key",
                    "size_bytes",
                    "duration_ms",
                ]
            )
        finalize_job(job_id)
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=exc, countdown=min(2 ** (self.request.retries + 1), 60)
            )
        logger.exception(
            "song_version_storage_failed job_id=%s index=%s", job_id, index
        )
        with transaction.atomic():
            version = (
                SongVersion.objects.select_for_update()
                .filter(job_id=job_id, index=index)
                .first()
            )
            if version and version.status != SongVersion.Status.READY:
                version.status = SongVersion.Status.FAILED
                version.save(update_fields=["status"])
        finalize_job(job_id)
