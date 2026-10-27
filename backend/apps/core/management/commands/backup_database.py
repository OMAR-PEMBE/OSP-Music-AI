from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.backup_storage import get_backup_storage_client

BACKUP_PREFIX = "osp-music/postgres/"
RETENTION_DAYS = 14


class Command(BaseCommand):
    help = "Upload a PostgreSQL custom-format dump to the private R2 backup bucket."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Local dump file to upload.")

    def handle(self, *args, **options):
        backup_path = Path(options["file"])
        if not backup_path.is_file():
            raise CommandError(f"Backup file does not exist: {backup_path}")
        if (
            not backup_path.name.startswith("osp-music-")
            or backup_path.suffix != ".dump"
        ):
            raise CommandError("Backup file must be named osp-music-*.dump.")

        client = get_backup_storage_client()
        key = f"{BACKUP_PREFIX}{backup_path.name}"
        with backup_path.open("rb") as backup_file:
            client.upload_fileobj(
                backup_file,
                settings.R2_BACKUP_BUCKET,
                key,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )

        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.R2_BACKUP_BUCKET,
            Prefix=BACKUP_PREFIX,
        ):
            expired_keys = [
                {"Key": item["Key"]}
                for item in page.get("Contents", [])
                if item["LastModified"] < cutoff
            ]
            for start in range(0, len(expired_keys), 1000):
                client.delete_objects(
                    Bucket=settings.R2_BACKUP_BUCKET,
                    Delete={"Objects": expired_keys[start : start + 1000]},
                )

        self.stdout.write(self.style.SUCCESS(f"Uploaded database backup: {key}"))
