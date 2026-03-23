from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0024_collaborator_offer_target_filters"),
    ]

    operations = [
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="product_sheet",
            field=models.FileField(
                blank=True,
                help_text="Opțional, recomandat la magazin (PDF/DOC/DOCX).",
                upload_to="collab_offer_sheets/",
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
                verbose_name="Fișă tehnică produs",
            ),
        ),
    ]
