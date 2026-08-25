# Soft-delete timestamp pentru LostFoundAnimal (păstrare 45 zile)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0086_lost_found_animal"),
    ]

    operations = [
        migrations.AddField(
            model_name="lostfoundanimal",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="La ștergere: is_active=False + deleted_at. Hard-delete după 45 zile.",
                null=True,
                verbose_name="Șters de user (soft)",
            ),
        ),
    ]
