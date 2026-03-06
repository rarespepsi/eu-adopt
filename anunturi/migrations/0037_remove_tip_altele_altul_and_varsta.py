# Șterge tip_altele_altul și varsta din modelul Pet.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("anunturi", "0036_tip_altele_free_text"),
    ]

    operations = [
        migrations.RemoveField(model_name="pet", name="tip_altele_altul"),
        migrations.RemoveField(model_name="pet", name="varsta"),
    ]
