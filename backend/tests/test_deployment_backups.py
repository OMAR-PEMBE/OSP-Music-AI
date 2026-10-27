from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone


def test_backup_command_uploads_dump_and_removes_expired_backups(tmp_path):
    backup_file = tmp_path / "osp-music-20260101T020000Z-abc.dump"
    backup_file.write_bytes(b"postgres dump")
    client = MagicMock()
    client.get_paginator.return_value.paginate.return_value = [
        {
            "Contents": [
                {
                    "Key": "osp-music/postgres/expired.dump",
                    "LastModified": timezone.now() - timedelta(days=15),
                },
                {
                    "Key": "osp-music/postgres/recent.dump",
                    "LastModified": timezone.now() - timedelta(days=1),
                },
            ]
        }
    ]
    uploaded_contents = []
    client.upload_fileobj.side_effect = (
        lambda file_obj, bucket, key, ExtraArgs: uploaded_contents.append(
            file_obj.read()
        )
    )

    with (
        patch(
            "apps.core.management.commands.backup_database.get_backup_storage_client",
            return_value=client,
        ),
        override_settings(R2_BACKUP_BUCKET="osp-music-backups"),
    ):
        call_command("backup_database", file=str(backup_file))

    client.upload_fileobj.assert_called_once()
    assert uploaded_contents == [b"postgres dump"]
    assert client.upload_fileobj.call_args.args[1:] == (
        "osp-music-backups",
        "osp-music/postgres/osp-music-20260101T020000Z-abc.dump",
    )
    client.delete_objects.assert_called_once_with(
        Bucket="osp-music-backups",
        Delete={"Objects": [{"Key": "osp-music/postgres/expired.dump"}]},
    )


def test_download_command_fetches_the_latest_backup(tmp_path):
    output_file = tmp_path / "restore.dump"
    client = MagicMock()
    client.get_paginator.return_value.paginate.return_value = [
        {
            "Contents": [
                {
                    "Key": "osp-music/postgres/old.dump",
                    "LastModified": timezone.now() - timedelta(days=2),
                },
                {
                    "Key": "osp-music/postgres/new.dump",
                    "LastModified": timezone.now() - timedelta(days=1),
                },
            ]
        }
    ]

    with (
        patch(
            "apps.core.management.commands.download_database_backup.get_backup_storage_client",
            return_value=client,
        ),
        override_settings(R2_BACKUP_BUCKET="osp-music-backups"),
        patch.object(
            client,
            "download_file",
            side_effect=lambda bucket, key, path: Path(path).write_bytes(b"restore"),
        ) as download_file,
    ):
        call_command("download_database_backup", output=str(output_file))

    download_file.assert_called_once_with(
        "osp-music-backups",
        "osp-music/postgres/new.dump",
        str(output_file),
    )
    assert output_file.exists()
