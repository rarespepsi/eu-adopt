"""
Email de bun venit trimis la crearea oricărui cont (PF, SRL, ONG, signup unificat).
"""
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


SUBJECT = "Bine ai venit în EU-Adopt 🐾"

BODY_TEMPLATE = """Bun venit în comunitatea EU-Adopt ❤️

Contul tău a fost creat cu succes și acum faci parte din platforma dedicată adopțiilor responsabile.

Datele tale de acces:
User: {{email_user}}

Te poți autentifica oricând folosind linkul de mai jos:
👉 {{link_login_site}}

Pentru siguranța contului tău, parola nu este transmisă prin email.

În EU-Adopt poți:
• descoperi animale care își caută o familie
• salva câinii preferați
• trimite cereri de adopție direct către adăposturi

Îți mulțumim că alegi să ajuți un animal să ajungă acasă.

EU-Adopt
We come to you.

––––––––––––––––––
Dacă nu ai creat tu acest cont, poți ignora acest mesaj.
"""


def send_welcome_email(user, request=None):
    """
    Trimite email de bun venit către noul membru după crearea contului.
    user: utilizatorul nou creat (trebuie să aibă user.email setat).
    request: opțional, pentru URL absolut la login; altfel se folosește SITE_URL.
    """
    if not user or not getattr(user, "email", None) or not user.email.strip():
        return False
    email_user = user.email.strip()
    if request:
        link_login_site = request.build_absolute_uri(reverse("login"))
    else:
        site = getattr(settings, "SITE_URL", "https://eu-adopt.ro").rstrip("/")
        link_login_site = site + reverse("login")
    body = BODY_TEMPLATE.replace("{{email_user}}", email_user).replace("{{link_login_site}}", link_login_site)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    try:
        send_mail(
            SUBJECT,
            body,
            from_email,
            [email_user],
            fail_silently=False,
        )
        try:
            from accounts.models import EmailDeliveryLog
            EmailDeliveryLog.objects.create(
                user=user,
                email_type="welcome",
                status="sent",
                to_email=email_user,
            )
        except Exception:
            pass
        return True
    except Exception as e:
        try:
            from accounts.models import EmailDeliveryLog
            EmailDeliveryLog.objects.create(
                user=user,
                email_type="welcome",
                status="failed",
                to_email=email_user,
                error_message=str(e),
            )
        except Exception:
            pass
        return False
