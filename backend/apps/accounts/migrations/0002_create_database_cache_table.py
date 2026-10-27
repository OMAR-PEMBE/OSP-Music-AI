from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command(
        "createcachetable",
        "django_cache",
        database=schema_editor.connection.alias,
        verbosity=0,
    )


def drop_cache_table(apps, schema_editor):
    quote = schema_editor.connection.ops.quote_name
    schema_editor.execute(f"DROP TABLE IF EXISTS {quote('django_cache')}")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
