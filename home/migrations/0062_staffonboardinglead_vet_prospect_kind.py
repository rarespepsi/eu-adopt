# Prospect cabinet colaborator: clinică (CV) vs farmacie veterinară (FV) — câmp separat de subtipul „cabinet”.

from django.db import migrations, models


def set_default_vet_cv_for_cabinet(apps, schema_editor):
    StaffOnboardingLead = apps.get_model("home", "StaffOnboardingLead")
    StaffOnboardingLead.objects.filter(
        account_kind="collaborator",
        collaborator_subtype="cabinet",
    ).exclude(vet_prospect_kind="fv").update(vet_prospect_kind="cv")


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0061_staff_lead_cv_merge_to_cabinet"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffonboardinglead",
            name="vet_prospect_kind",
            field=models.CharField(
                blank=True,
                choices=[("", "—"), ("cv", "CV"), ("fv", "FV")],
                db_index=True,
                default="",
                help_text="Doar pentru colaborator cu tip cabinet: clinică (CV) sau farmacie (FV).",
                max_length=3,
                verbose_name="Prospect vet. (cabinet colab.)",
            ),
        ),
        migrations.RunPython(set_default_vet_cv_for_cabinet, migrations.RunPython.noop),
    ]
