# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0045_publicitate_creative_access_and_line"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteCartCheckoutIntent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_method", models.CharField(choices=[
                    ("card_online", "Card bancar online (Visa / Mastercard)"),
                    ("bank_transfer", "Transfer bancar / ordin de plată (OP)"),
                    ("installments", "Plată în rate (bancă partener — confirmare manuală)"),
                    ("cod_courier", "Ramburs la livrare (curier)"),
                    ("cash_pos", "Numerar sau card POS la punct de lucru / partener"),
                    ("company_invoice", "Factură pe firmă (date din fișă / completare manuală)"),
                ], max_length=32, verbose_name="Mod de plată")),
                ("buyer_full_name", models.CharField(max_length=160, verbose_name="Nume complet")),
                ("buyer_email", models.EmailField(max_length=254, verbose_name="E-mail")),
                ("buyer_phone", models.CharField(blank=True, default="", max_length=40, verbose_name="Telefon")),
                ("buyer_county", models.CharField(blank=True, default="", max_length=120, verbose_name="Județ")),
                ("buyer_city", models.CharField(blank=True, default="", max_length=120, verbose_name="Oraș / localitate")),
                ("buyer_address", models.CharField(blank=True, default="", max_length=500, verbose_name="Adresă livrare / observații adresă")),
                ("buyer_company_display", models.CharField(blank=True, default="", max_length=255, verbose_name="Firmă (afișat)")),
                ("buyer_company_legal", models.CharField(blank=True, default="", max_length=255, verbose_name="Denumire juridică")),
                ("buyer_company_cui", models.CharField(blank=True, default="", max_length=40, verbose_name="CUI / CIF")),
                ("lines_json", models.JSONField(default=list, verbose_name="Linii coș (snapshot)")),
                ("total_lei", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Total estimativ (lei)")),
                ("unpriced_count", models.PositiveSmallIntegerField(default=0, verbose_name="Articole fără sumă în titlu")),
                ("buyer_note", models.TextField(blank=True, default="", verbose_name="Mesaj pentru echipă")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_cart_checkout_intents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Cerere plată coș site",
                "verbose_name_plural": "Cereri plată coș site",
                "ordering": ["-created_at"],
            },
        ),
    ]
