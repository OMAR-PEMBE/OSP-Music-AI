from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.backup_storage import get_backup_storage_client
from apps.core.management.commands.backup_database import BACKUP_PREFIX


class Command(BaseCommand):
    help = "Download the latest PostgreSQL backup from the private R2 bucket."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="Local output file.")

    def handle(self, *args, **options):
        client = get_backup_storage_client()
        paginator = client.get_paginator("list_objects_v2")
        backups = [
            item
            for page in paginator.paginate(
                Bucket=settings.R2_BACKUP_BUCKET,
                Prefix=BACKUP_PREFIX,
            )
            for item in page.get("Contents", [])
            if item["Key"].endswith(".dump")
        ]
        if not backups:
            raise CommandError("No database backups were found in R2.")

        latest = max(backups, key=lambda item: item["LastModified"])
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(
            settings.R2_BACKUP_BUCKET,
            latest["Key"],
            str(output_path),
        )
        output_path.chmod(0o600)
        self.stdout.write(
            self.style.SUCCESS(
                f"Downloaded latest database backup ({latest['Key']}) to {output_path}."
            )
        )
