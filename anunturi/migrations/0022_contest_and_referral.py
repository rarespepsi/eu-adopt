# Generated migration for Contest and ReferralVisit models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('anunturi', '0021_newsletter_and_presentation'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nume concurs')),
                ('start_date', models.DateTimeField(verbose_name='Data început')),
                ('end_date', models.DateTimeField(verbose_name='Data sfârșit')),
                ('prize_title', models.CharField(blank=True, max_length=200, verbose_name='Titlu premiu')),
                ('prize_image', models.ImageField(blank=True, null=True, upload_to='contest_prizes/', verbose_name='Imagine premiu')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activ')),
            ],
            options={
                'verbose_name': 'Concurs',
                'verbose_name_plural': 'Concursuri',
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='ReferralVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ref_code', models.CharField(db_index=True, max_length=100, verbose_name='Cod referral')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data vizită')),
                ('ip_hash', models.CharField(db_index=True, max_length=64, verbose_name='Hash IP')),
                ('counted', models.BooleanField(db_index=True, default=False, verbose_name='Contorizat')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referral_visits', to=settings.AUTH_USER_MODEL, verbose_name='Utilizator')),
            ],
            options={
                'verbose_name': 'Vizită referral',
                'verbose_name_plural': 'Vizite referral',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='referralvisit',
            index=models.Index(fields=['ref_code', 'ip_hash', 'timestamp'], name='anunturi_re_ref_cod_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='referralvisit',
            index=models.Index(fields=['user', 'counted'], name='anunturi_re_user_id_counted_idx'),
        ),
    ]
