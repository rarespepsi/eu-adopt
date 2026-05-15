# Unificare: prescurtarea istorică „cv” (cabinet veterinar) → valoare canonică „cabinet”;
# eticheta afișată pentru „cabinet” devine „CV” (home.models StaffOnboardingLead.COLLAB_SUBTYPE_CHOICES).

from django.db import migrations, models


def merge_cv_to_cabinet(apps, schema_editor):
    StaffOnboardingLead = apps.get_model("home", "StaffOnboardingLead")
    StaffOnboardingLead.objects.filter(collaborator_subtype="cv").update(collaborator_subtype="cabinet")


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0060_staff_lead_collab_grooming_choice"),
    ]

    operations = [
        migrations.RunPython(merge_cv_to_cabinet, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="staffonboardinglead",
            name="collaborator_subtype",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "—"),
                    ("cabinet", "CV"),
                    ("servicii", "Servicii (altele)"),
                    ("magazin", "Magazin"),
                    ("grooming", "Grooming"),
                    ("transport", "Transportator"),
                    ("adpub", "ADPUB"),
                    ("adprv", "ADPRV"),
                ],
                default="",
                max_length=20,
                verbose_name="Tip colaborator",
            ),
        ),
    ]
