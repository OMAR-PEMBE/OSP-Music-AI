import uuid

from django.conf import settings
from django.db import models


class SongJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SUBMITTING = "submitting", "Submitting"
        RUNNING = "running", "Running"
        STREAMING = "streaming", "Streaming"
        READY = "ready", "Ready"
        PARTIAL = "partial", "Partly ready"
        FAILED = "failed", "Failed"

    class LyricsSource(models.TextChoices):
        USER = "user", "User supplied"
        GENERATED = "generated", "Generated"

    class Engine(models.TextChoices):
        MUREKA = "mureka", "Mureka"
        SUNO = "suno", "Suno"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="song_jobs",
        db_index=True,
    )
    client_request_id = models.UUIDField(default=uuid.uuid4)
    title = models.CharField(max_length=120, blank=True, default="")
    idea = models.TextField(blank=True, default="")
    genre = models.CharField(max_length=30, blank=True, default="")
    genre_other = models.CharField(max_length=30, blank=True, default="")
    language = models.CharField(max_length=10, blank=True, default="sw")
    voice = models.CharField(max_length=6, blank=True, default="auto")
    lyrics = models.TextField(blank=True, default="")
    lyrics_source = models.CharField(
        max_length=10,
        choices=LyricsSource.choices,
        default=LyricsSource.USER,
    )
    engine = models.CharField(
        max_length=20,
        choices=Engine.choices,
        default=Engine.MUREKA,
    )
    model = models.CharField(max_length=30, default="mureka-9")
    versions_requested = models.PositiveSmallIntegerField(default=2)
    price_tzs = models.BigIntegerField()
    est_cost_usd_cents = models.PositiveIntegerField(default=10)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    provider_task_id = models.CharField(
        max_length=64, null=True, blank=True, unique=True
    )
    provider_trace_id = models.CharField(max_length=64, null=True, blank=True)
    provider_status = models.CharField(max_length=20, null=True, blank=True)
    capacity_error_since = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    poll_attempts = models.PositiveIntegerField(default=0)
    settled_at = models.DateTimeField(null=True, blank=True)
    seen_by_user = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price_tzs__gt=0),
                name="song_job_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(versions_requested=2),
                name="song_job_requests_two_versions",
            ),
            models.UniqueConstraint(
                fields=["user", "client_request_id"],
                name="song_job_user_request_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"], name="song_user_created_idx"),
            models.Index(
                fields=["status", "created_at"], name="song_status_created_idx"
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title or str(self.pk)


class SongVersion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        STREAMING = "streaming", "Streaming"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        SongJob,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    index = models.PositiveSmallIntegerField()
    provider_song_id = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    stream_url = models.TextField(null=True, blank=True)
    storage_key = models.CharField(max_length=255, null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "index"],
                name="song_version_job_index_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(index__in=[0, 1]),
                name="song_version_index_valid",
            ),
        ]
        ordering = ["index"]


class LyricsRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lyrics_requests",
        db_index=True,
    )
    prompt = models.TextField()
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
