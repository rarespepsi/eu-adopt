# Categorii (grupuri) de utilizatori la logare

from django.db import migrations


def create_user_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ["Vizitator", "Asociație", "Administrator"]:
        Group.objects.get_or_create(name=name)


def remove_user_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Vizitator", "Asociație", "Administrator"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("anunturi", "0006_ridicare_personala"),
    ]

    operations = [
        migrations.RunPython(create_user_groups, remove_user_groups),
    ]
