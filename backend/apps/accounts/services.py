import logging

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.core.models import SupportMessage
from apps.songs.models import LyricsRequest, SongJob, SongVersion

logger = logging.getLogger(__name__)


class AccountDeletionStorageError(Exception):
    pass


def delete_account(user, password):
    user_model = get_user_model()
    with transaction.atomic():
        locked_user = user_model.objects.select_for_update().get(pk=user.pk)
        if (
            not locked_user.is_active
            or locked_user.deleted_at
            or not locked_user.check_password(password)
        ):
            return False

        jobs = list(
            SongJob.objects.select_for_update().filter(user=locked_user).order_by("pk")
        )
        job_ids = [job.pk for job in jobs]
        versions = list(
            SongVersion.objects.filter(job_id__in=job_ids).values_list(
                "job_id", "index", "storage_key"
            )
        )
        storage_keys = {
            key
            for job_id, index, key in versions
            for key in (key, f"songs/{locked_user.pk}/{job_id}/{index}.mp3")
            if key
        }
        if locked_user.avatar:
            storage_keys.add(locked_user.avatar)

        try:
            for key in storage_keys:
                default_storage.delete(key)
        except Exception as error:
            logger.exception("account_delete_storage_failed user_id=%s", locked_user.pk)
            raise AccountDeletionStorageError from error

        if job_ids:
            SongVersion.objects.filter(job_id__in=job_ids).delete()
            SongJob.objects.filter(pk__in=job_ids).update(
                title="",
                idea="",
                lyrics="",
                deleted_at=timezone.now(),
                updated_at=timezone.now(),
            )
        LyricsRequest.objects.filter(user=locked_user).delete()
        SupportMessage.objects.filter(user=locked_user).delete()
        EmailAddress.objects.filter(user=locked_user).delete()

        user_id = locked_user.pk
        locked_user.email = f"deleted-{user_id}@deleted.local"
        locked_user.first_name = ""
        locked_user.last_name = ""
        locked_user.display_name = f"deleted-{user_id.hex[:22]}"
        locked_user.avatar = None
        locked_user.phone_last_used = None
        locked_user.is_active = False
        locked_user.deleted_at = timezone.now()
        locked_user.save(
            update_fields=[
                "email",
                "first_name",
                "last_name",
                "display_name",
                "avatar",
                "phone_last_used",
                "is_active",
                "deleted_at",
            ]
        )

    return True
