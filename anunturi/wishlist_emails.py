"""
Helper pentru emailuri wishlist: link unsubscribe (signed), limită 7 zile, trimitere HTML+plain.
"""
from django.core.mail import EmailMultiAlternatives
from django.core.signing import Signer
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

signer = Signer()


def get_unsubscribe_url(user, request=None):
    """Link signed pentru dezabonare – folosit în toate emailurile wishlist."""
    token = signer.sign(str(user.pk))
    path = reverse("wishlist_unsubscribe", kwargs={"signed": token})
    if request:
        return request.build_absolute_uri(path)
    site_url = getattr(settings, "SITE_URL", "https://eu-adopt.ro").rstrip("/")
    return f"{site_url}{path}"


def can_send_wishlist_email(profile):
    """Max 1 wishlist email per user la 7 zile (pentru reminder 72h și 30z). Emailul „adoptat” nu e blocat."""
    if not profile or not getattr(profile, "last_wishlist_email_at", None):
        return True
    return profile.last_wishlist_email_at <= timezone.now() - timedelta(days=7)


def send_wishlist_email(subject, body_plain, to_email, from_email=None, html_body=None, user_for_unsubscribe=None, request=None):
    """
    Trimite email cu optional HTML. Dacă user_for_unsubscribe e dat, adaugă la sfârșitul textului
    un paragraf cu link dezabonare (în plain și în HTML).
    """
    from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    if user_for_unsubscribe:
        unsub_url = get_unsubscribe_url(user_for_unsubscribe, request)
        body_plain += f"\n\n---\nNu mai dorești notificări wishlist? Dezabonare: {unsub_url}"
        if html_body:
            html_body += f'<p style="font-size:12px;color:#666;"><a href="{unsub_url}">Dezabonare notificări wishlist</a></p>'
    msg = EmailMultiAlternatives(subject, body_plain, from_email, [to_email])
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
