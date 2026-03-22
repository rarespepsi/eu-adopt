# Generated manually for collaborator offer email deduplication flags

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0020_collaborator_offer_validity_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="expiry_notice_sent_for_valid_until",
            field=models.DateField(
                blank=True,
                help_text="Dacă e setat la aceeași valoare ca valid_until, nu mai trimitem iar mailul T−5 zile.",
                null=True,
                verbose_name="Reminder expirare trimis pentru data sfârșit",
            ),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="low_stock_notice_sent",
            field=models.BooleanField(
                default=False,
                help_text="True după mailul „mai ai 1 ofertă”; se resetează la creșterea stocului în fișă.",
                verbose_name="Reminder stoc 1 rămas trimis",
            ),
        ),
    ]
