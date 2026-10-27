from django.db import migrations, models


def migrate_language_preferences(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(language="sw").update(language="en")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_managers"),
    ]

    operations = [
        migrations.RunPython(migrate_language_preferences, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="language",
            field=models.CharField(
                choices=[("en", "English")],
                default="en",
                max_length=2,
            ),
        ),
    ]
