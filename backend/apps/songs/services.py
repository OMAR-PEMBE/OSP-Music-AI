from django.db import transaction
from django.utils import timezone

from apps.wallet.services import settle_song_job

from .models import SongJob, SongVersion

GENRE_TAGS = {
    "bongo_flava": "bongo flava, east african pop, swahili",
    "rnb": "r&b, smooth, soulful",
    "afrobeats": "afrobeats, west african groove",
    "amapiano": "amapiano, log drum, south african house",
    "gospel": "african gospel, choir, uplifting",
    "hiphop": "hip hop, rap",
}
LANG_TAGS = {
    "sw": "swahili lyrics",
    "en": "english lyrics",
    "mixed": "swahili and english lyrics",
}
LYRICS_LANGUAGE_INSTRUCTIONS = {
    "sw": "Andika mashairi kwa Kiswahili",
    "en": "Write lyrics in English",
    "mixed": "Write lyrics mixing Kiswahili and English",
}


def build_style_prompt(*, genre, language, voice, idea, genre_other=""):
    genre_tag = GENRE_TAGS.get(genre) or genre_other.strip()
    voice_tag = f"{voice} vocal" if voice != "auto" else "natural vocal"
    short_idea = " ".join(idea.split())[:160]
    parts = [genre_tag, LANG_TAGS[language], voice_tag, short_idea]
    return ", ".join(part for part in parts if part)[:1024]


def build_lyrics_prompt(*, genre, language, idea, genre_other=""):
    genre_text = genre_other.strip() if genre == "other" else genre.replace("_", " ")
    return (
        f"{LYRICS_LANGUAGE_INSTRUCTIONS[language]}. Genre: {genre_text}. "
        f"Song about: {idea}. Use [Verse], [Chorus], [Bridge] sections."
    )


def finalize_job(job_id):
    with transaction.atomic():
        job = SongJob.objects.select_for_update().get(pk=job_id)
        if job.deleted_at:
            return job
        if job.settled_at:
            return job
        versions = list(job.versions.all())
        if len(versions) != job.versions_requested or any(
            version.status in {SongVersion.Status.PENDING, SongVersion.Status.STREAMING}
            for version in versions
        ):
            return job

        ready_count = sum(
            version.status == SongVersion.Status.READY for version in versions
        )
        job.status = (
            SongJob.Status.READY
            if ready_count == job.versions_requested
            else SongJob.Status.PARTIAL if ready_count else SongJob.Status.FAILED
        )
        job.finished_at = timezone.now()
        job.seen_by_user = False
        job.save(update_fields=["status", "finished_at", "seen_by_user", "updated_at"])
        settle_song_job(job)
        return job


def fail_job(job_id, *, reason, provider_status=None, trace_id=None):
    with transaction.atomic():
        job = SongJob.objects.select_for_update().get(pk=job_id)
        if job.deleted_at:
            return job
        if job.settled_at:
            return job
        job.failure_reason = reason[:255]
        if provider_status:
            job.provider_status = provider_status[:20]
        if trace_id:
            job.provider_trace_id = trace_id[:64]
        job.save(
            update_fields=[
                "failure_reason",
                "provider_status",
                "provider_trace_id",
                "updated_at",
            ]
        )
        job.versions.exclude(status=SongVersion.Status.READY).update(
            status=SongVersion.Status.FAILED
        )
    return finalize_job(job_id)
