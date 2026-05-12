# Generated manually for staff lead invite tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0056_staff_onboarding_lead_fisa_csv"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffonboardinglead",
            name="invite_email_last_sent_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Ultima invitație email (staff)",
            ),
        ),
    ]
