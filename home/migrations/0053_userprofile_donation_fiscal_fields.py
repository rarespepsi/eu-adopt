from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0052_publicitateorder_contract_posting_email_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="company_reg_com",
            field=models.CharField(
                "Nr. Reg. Com. / J", max_length=64, blank=True, default=""
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="company_representative",
            field=models.CharField(
                "Reprezentant legal (firmă)", max_length=255, blank=True, default=""
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="donation_cnp",
            field=models.CharField(
                "CNP (opțional, documente donații)", max_length=13, blank=True, default=""
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="donation_address",
            field=models.CharField(
                "Adresă completă (donații / documente)", max_length=500, blank=True, default=""
            ),
        ),
    ]
