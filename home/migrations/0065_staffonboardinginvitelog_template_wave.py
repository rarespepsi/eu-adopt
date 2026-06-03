# Faza B — șablon + tip val pe log invitații

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0064_staff_onboarding_invite_control"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffonboardinginvitelog",
            name="template_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=20,
                verbose_name="Șablon categorie",
            ),
        ),
        migrations.AddField(
            model_name="staffonboardinginvitelog",
            name="dispatch_kind",
            field=models.CharField(
                choices=[("manual", "Bifă manuală"), ("wave", "Val (filtru)")],
                db_index=True,
                default="manual",
                max_length=10,
                verbose_name="Mod trimitere",
            ),
        ),
    ]
