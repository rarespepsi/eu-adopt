from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0026_collaborator_offer_species_checkboxes"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoA2Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payer_email", models.EmailField(max_length=254, verbose_name="Email plătitor")),
                ("payer_name_snapshot", models.CharField(blank=True, max_length=200, verbose_name="Nume plătitor (snapshot)")),
                ("package", models.CharField(choices=[("6h", "6h"), ("12h", "12h")], default="6h", max_length=8, verbose_name="Pachet")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="Cantitate")),
                ("unit_price", models.PositiveIntegerField(default=10, verbose_name="Preț unitar (lei)")),
                ("total_price", models.PositiveIntegerField(default=10, verbose_name="Total (lei)")),
                ("payment_method", models.CharField(default="card", max_length=20, verbose_name="Metodă plată")),
                ("schedule", models.CharField(default="intercalat", max_length=20, verbose_name="Programare")),
                ("start_date", models.DateField(verbose_name="Data start")),
                ("starts_at", models.DateTimeField(blank=True, null=True, verbose_name="Pornire promovare")),
                ("ends_at", models.DateTimeField(blank=True, null=True, verbose_name="Final promovare")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("checkout_pending", "Checkout pending"), ("paid", "Paid"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="draft", max_length=24, verbose_name="Status")),
                ("payment_provider", models.CharField(blank=True, default="demo", max_length=40, verbose_name="Procesator")),
                ("payment_ref", models.CharField(blank=True, max_length=120, verbose_name="Referință plată")),
                ("summary_sent_at", models.DateTimeField(blank=True, null=True, verbose_name="Rezumat final trimis la")),
                ("summary_manual_sent_at", models.DateTimeField(blank=True, null=True, verbose_name="Rezumat trimis manual la")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("payer_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="promo_a2_orders", to=settings.AUTH_USER_MODEL)),
                ("pet", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="promo_a2_orders", to="home.animallisting")),
            ],
            options={
                "verbose_name": "Comandă promovare A2",
                "verbose_name_plural": "Comenzi promovare A2",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="promoa2order",
            index=models.Index(fields=["status", "ends_at"], name="home_promoa_status_202928_idx"),
        ),
        migrations.AddIndex(
            model_name="promoa2order",
            index=models.Index(fields=["payer_email", "created_at"], name="home_promoa_payer_e_301f96_idx"),
        ),
    ]
