# Generated manually for SiteCartItem

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0039_publicitate_order"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteCartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ref_key", models.CharField(db_index=True, max_length=96)),
                ("kind", models.CharField(choices=[
                    ("servicii_offer", "Ofertă Servicii"),
                    ("shop", "Shop"),
                    ("shop_custom", "Shop produse personalizate"),
                    ("shop_foto", "Magazin foto"),
                ], max_length=32)),
                ("title", models.CharField(max_length=220)),
                ("detail_url", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_cart_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="sitecartitem",
            index=models.Index(fields=["user", "created_at"], name="home_sitecar_user_id_2b8f1e_idx"),
        ),
        migrations.AddConstraint(
            model_name="sitecartitem",
            constraint=models.UniqueConstraint(fields=("user", "ref_key"), name="home_sitecartitem_user_refkey_uniq"),
        ),
    ]
