# partner_kind: canal snapshot pentru zonă Servicii (S3/S5/S4)

from django.db import migrations, models


def backfill_partner_kind(apps, schema_editor):
    """
    Înainte de partner_kind, listarea publică veterinar folosea doar profil cabinet.
    Toate rândurile existente rămân cabinet → rămân vizibile în S3 chiar dacă userul
    și-a schimbat între timp bifa în cont (servicii).
    """
    CollaboratorServiceOffer = apps.get_model("home", "CollaboratorServiceOffer")
    CollaboratorServiceOffer.objects.all().update(partner_kind="cabinet")


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0021_collaborator_offer_notification_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="partner_kind",
            field=models.CharField(
                choices=[
                    ("cabinet", "Cabinet / clinică veterinară"),
                    ("servicii", "Servicii / grooming / dresaj"),
                    ("magazin", "Magazin / pet-shop"),
                ],
                db_index=True,
                default="cabinet",
                help_text="Setat la publicare; determină zona Servicii. Nu se schimbă cu bifa din cont.",
                max_length=20,
                verbose_name="Canal partener (la creare)",
            ),
        ),
        migrations.AddIndex(
            model_name="collaboratorserviceoffer",
            index=models.Index(
                fields=["partner_kind", "is_active", "created_at"],
                name="home_collab_partner_7a8b2c_idx",
            ),
        ),
        migrations.RunPython(backfill_partner_kind, migrations.RunPython.noop),
    ]
