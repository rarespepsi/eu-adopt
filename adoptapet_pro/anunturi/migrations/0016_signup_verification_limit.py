# Generated manually for limitare încercări verificare SMS la înregistrare

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('anunturi', '0015_ong_profile_pfa_af'),
    ]

    operations = [
        migrations.CreateModel(
            name='SignupVerificationFail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='signup_verification_fails', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Eșec verificare înregistrare',
                'verbose_name_plural': 'Eșecuri verificare înregistrare',
                'ordering': ['-attempted_at'],
            },
        ),
        migrations.CreateModel(
            name='SignupVerificationLock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('locked_until', models.DateTimeField(verbose_name='Blocat până la')),
                ('user', models.OneToOneField(on_delete=models.CASCADE, related_name='signup_verification_lock', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Blocare verificare înregistrare',
                'verbose_name_plural': 'Blocări verificare înregistrare',
            },
        ),
    ]
