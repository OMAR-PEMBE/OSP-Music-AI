import logging
import re
from datetime import datetime, time, timedelta

from django.core.files.storage import default_storage
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.models import get_app_settings
from apps.wallet.permissions import IsEmailVerified
from apps.wallet.services import charge_song

from .models import LyricsRequest, SongJob, SongVersion
from .serializers import (
    LyricsSerializer,
    SongCreateSerializer,
    SongJobSerializer,
    parse_idempotency_key,
)
from .services import build_lyrics_prompt
from .storage import signed_audio_url

logger = logging.getLogger(__name__)


class GenerationPaused(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Music generation is paused."
    default_code = "generation_paused"


class LyricsLimitReached(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Daily lyrics limit reached."
    default_code = "lyrics_limit_reached"


class UserRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many song requests."
    default_code = "rate_limited"


class LyricsView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def post(self, request):
        serializer = LyricsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app_settings = get_app_settings()
        if not app_settings.generation_enabled:
            raise GenerationPaused()

        values = serializer.validated_data
        prompt = build_lyrics_prompt(**values)
        local_day = timezone.localdate()
        day_start = timezone.make_aware(datetime.combine(local_day, time.min))
        next_day = day_start + timedelta(days=1)
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            attempts = LyricsRequest.objects.filter(
                user_id=request.user.pk,
                created_at__gte=day_start,
                created_at__lt=next_day,
            ).count()
            if attempts >= app_settings.lyrics_daily_limit:
                raise LyricsLimitReached()
            lyrics_request = LyricsRequest.objects.create(
                user=request.user,
                prompt=prompt,
                success=False,
            )

        from engines.factory import get_engine_for_lyrics
        from engines.mureka import MurekaError

        try:
            result = get_engine_for_lyrics().generate_lyrics(prompt)
        except Exception as exc:
            logger.exception(
                "lyrics_generation_failed request_id=%s", lyrics_request.pk
            )
            if isinstance(exc, MurekaError) and exc.trace_id:
                logger.error("mureka_lyrics_trace_id=%s", exc.trace_id)
            raise GenerationPaused() from exc

        lyrics_request.success = True
        lyrics_request.save(update_fields=["success"])
        return Response(
            {
                "title": result.title[:120],
                "lyrics": result.lyrics[:5000],
                "remaining_today": max(
                    app_settings.lyrics_daily_limit - attempts - 1,
                    0,
                ),
            }
        )


class SongsView(ListAPIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]
    serializer_class = SongJobSerializer

    def get_queryset(self):
        queryset = (
            SongJob.objects.filter(
                user_id=self.request.user.pk, deleted_at__isnull=True
            )
            .prefetch_related("versions")
            .order_by("-created_at", "-id")
        )
        job_status = self.request.query_params.get("status")
        if job_status in SongJob.Status.values:
            queryset = queryset.filter(status=job_status)
        return queryset

    def post(self, request):
        serializer = SongCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_request_id = parse_idempotency_key(
            request.headers.get("Idempotency-Key")
        )
        app_settings = get_app_settings()
        if not app_settings.generation_enabled:
            raise GenerationPaused()

        now = timezone.now()
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=request.user.pk)
            existing = SongJob.objects.filter(
                user=locked_user,
                client_request_id=client_request_id,
                deleted_at__isnull=True,
            ).first()
            if existing:
                return Response(
                    SongJobSerializer(existing).data,
                    status=status.HTTP_200_OK,
                )
            if (
                SongJob.objects.filter(
                    user=locked_user,
                    created_at__gte=now - timedelta(minutes=1),
                ).count()
                >= 6
            ):
                raise UserRateLimited()

            values = serializer.validated_data
            price_tzs = app_settings.song_price_tzs
            if values["lyrics"]:
                title = values["idea"][:120]
                lyrics_source = SongJob.LyricsSource.USER
            else:
                title = values["idea"][:120]
                lyrics_source = SongJob.LyricsSource.GENERATED
            from engines.router import estimate_request_cost_usd_cents

            engine = app_settings.active_engine
            estimated_cost = estimate_request_cost_usd_cents(
                app_settings, engine, needs_lyrics=not bool(values["lyrics"])
            )
            if estimated_cost is None:
                raise GenerationPaused()
            job = SongJob.objects.create(
                user=locked_user,
                client_request_id=client_request_id,
                title=title,
                idea=values["idea"],
                genre=values["genre"],
                genre_other=values.get("genre_other", "").strip()[:30],
                language=values["language"],
                voice=values["voice"],
                lyrics=values["lyrics"],
                lyrics_source=lyrics_source,
                engine=engine,
                model=app_settings.mureka_model if engine == "mureka" else "",
                versions_requested=2,
                price_tzs=price_tzs,
                est_cost_usd_cents=estimated_cost,
                status=SongJob.Status.QUEUED,
            )
            SongVersion.objects.bulk_create(
                [
                    SongVersion(job=job, index=0),
                    SongVersion(job=job, index=1),
                ]
            )
            charge_song(locked_user, job, price_tzs)

        return Response(SongJobSerializer(job).data, status=status.HTTP_201_CREATED)


class SongDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get_job(self, request, job_id):
        try:
            return (
                SongJob.objects.filter(
                    user_id=request.user.pk,
                    deleted_at__isnull=True,
                )
                .prefetch_related("versions")
                .get(pk=job_id)
            )
        except (SongJob.DoesNotExist, ValueError):
            raise NotFound()

    def get(self, request, job_id):
        return Response(SongJobSerializer(self.get_job(request, job_id)).data)

    def patch(self, request, job_id):
        job = self.get_job(request, job_id)
        title = request.data.get("title")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
            raise ValidationError({"title": "Title must contain 1 to 120 characters."})
        job.title = title.strip()
        job.save(update_fields=["title", "updated_at"])
        return Response(SongJobSerializer(job).data)

    def delete(self, request, job_id):
        job = self.get_job(request, job_id)
        keys = list(
            job.versions.exclude(storage_key__isnull=True)
            .exclude(storage_key="")
            .values_list("storage_key", flat=True)
        )
        for key in keys:
            try:
                default_storage.delete(key)
            except Exception:
                logger.exception("song_file_delete_failed job_id=%s", job.pk)
        job.deleted_at = timezone.now()
        job.save(update_fields=["deleted_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AudioRedirectView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get(self, request, job_id, index):
        try:
            job = SongJob.objects.get(
                pk=job_id,
                user_id=request.user.pk,
                deleted_at__isnull=True,
            )
            version = job.versions.get(index=index)
        except (SongJob.DoesNotExist, SongVersion.DoesNotExist, ValueError):
            raise NotFound()
        if version.status != SongVersion.Status.READY or not version.storage_key:
            raise NotFound()
        parameters = None
        if request.query_params.get("download") == "1":
            letter = "A" if index == 0 else "B"
            safe_title = re.sub(r"[^A-Za-z0-9 _-]", "", job.title).strip() or "Song"
            filename = f"{safe_title} - {letter}.mp3"
            parameters = {
                "ResponseContentDisposition": f'attachment; filename="{filename}"'
            }
        return HttpResponseRedirect(
            signed_audio_url(version.storage_key, parameters=parameters, expire=600)
        )


class MarkSongsSeenView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def post(self, request):
        SongJob.objects.filter(
            user_id=request.user.pk,
            deleted_at__isnull=True,
            seen_by_user=False,
        ).update(seen_by_user=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
