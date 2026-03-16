#!/usr/bin/env python
"""Trimite un email de verificare la rarespepsi@yahoo.com."""
import os
from pathlib import Path
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import Signer
from django.urls import reverse
from urllib.parse import quote

User = get_user_model()
email = 'rarespepsi@yahoo.com'
u = User.objects.filter(email=email).first()
if not u:
    print('User cu', email, 'negasit.')
else:
    signer = Signer()
    token = signer.sign(u.pk)
    base = 'http://127.0.0.1:8000'
    verify_url = base + reverse('signup_verify_email') + '?token=' + quote(token)
    plain_msg = 'Buna ziua,\n\nApasa pe link pentru a-ti activa contul:\n' + verify_url + '\n\nDaca nu ai creat cont, poti ignora acest email.'
    html_msg = (
        '<p>Buna ziua,</p>'
        '<p>Apasa pe link pentru a-ti activa contul:<br/>'
        '<a href="' + verify_url + '" style="color:#1565c0;font-weight:bold;">Activeaza contul</a></p>'
        '<p>Daca linkul nu merge, copiaza in browser:</p><p style="word-break:break-all;">' + verify_url + '</p>'
        '<p>Daca nu ai creat cont, poti ignora acest email.</p>'
    )
    send_mail(
        subject='Verificare email – EU-Adopt',
        message=plain_msg,
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
        html_message=html_msg,
    )
    print('Email trimis la', email)
    print('Link:', verify_url[:90] + '...')
