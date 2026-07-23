# Generated manually for ReclamaSlotNote.market (RO vs EU pub)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0075_userprofile_promo_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="reclamaslotnote",
            name="market",
            field=models.CharField(
                choices=[("ro", "Publi RO (.ro)"), ("eu", "Publi EU (.com + oglindă TLD)")],
                db_index=True,
                default="ro",
                help_text="RO = clienți .ro; EU = creatives staff pe .com/.de/.fr/.es (fără .ro).",
                max_length=8,
                verbose_name="Piață",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="reclamaslotnote",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="reclamaslotnote",
            constraint=models.UniqueConstraint(
                fields=("section", "slot_code", "market"),
                name="home_reclamaslotnote_section_slot_market_uniq",
            ),
        ),
        migrations.AlterModelOptions(
            name="reclamaslotnote",
            options={
                "ordering": ["market", "section", "slot_code"],
                "verbose_name": "Notiță slot Reclama",
                "verbose_name_plural": "Notițe sloturi Reclama",
            },
        ),
    ]
