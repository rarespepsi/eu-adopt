# Adaugă kind „publicitate” pentru linii mutate din coșul publicitate în coșul site.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0043_adoption_pending_owner_reminders"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitecartitem",
            name="kind",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("servicii_offer", "Ofertă Servicii"),
                    ("shop", "Shop"),
                    ("shop_custom", "Shop produse personalizate"),
                    ("shop_foto", "Magazin foto"),
                    ("publicitate", "Publicitate"),
                ],
            ),
        ),
    ]
