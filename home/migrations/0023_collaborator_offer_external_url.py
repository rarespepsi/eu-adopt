from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0022_collaborator_offer_partner_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="external_url",
            field=models.URLField(
                blank=True,
                help_text="Opțional pentru servicii/cabinet; recomandat/obligatoriu la magazin (http/https).",
                max_length=500,
                verbose_name="Link produs (extern)",
            ),
        ),
    ]
