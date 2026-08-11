# Generated manually for Facebook outbound posts

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0079_campanie_sterilizare"),
    ]

    operations = [
        migrations.CreateModel(
            name="FacebookOutboundPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("animal", "Animal"), ("campanie", "Campanie sterilizare")], db_index=True, max_length=20)),
                ("object_id", models.PositiveIntegerField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "În așteptare"),
                            ("posted", "Postat"),
                            ("failed", "Eșuat"),
                            ("skipped", "Omis"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("facebook_post_id", models.CharField(blank=True, default="", max_length=64)),
                ("error", models.CharField(blank=True, default="", max_length=500)),
                ("posted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Postare Facebook",
                "verbose_name_plural": "Postări Facebook",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="facebookoutboundpost",
            index=models.Index(fields=["status", "created_at"], name="home_facebo_status_c8a2c1_idx"),
        ),
        migrations.AddIndex(
            model_name="facebookoutboundpost",
            index=models.Index(fields=["posted_at"], name="home_facebo_posted__a1b2c3_idx"),
        ),
        migrations.AddConstraint(
            model_name="facebookoutboundpost",
            constraint=models.UniqueConstraint(fields=("kind", "object_id"), name="uniq_fb_outbound_kind_object"),
        ),
    ]
