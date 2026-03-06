"""
Semnale: notificare utilizatori când un animal din wishlist este adoptat;
email către proprietor la creare cerere adopție.
"""
import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail

from .models import Pet, PetFavorite, AdoptionRequest
from .wishlist_emails import send_wishlist_email

logger = logging.getLogger(__name__)


def _recommended_pets_for_adopted(pet, limit=3):
    """3 animale recomandate: același tip, mărime, vârstă aproximativă; exclude adopted/unavailable."""
    qs = Pet.objects.filter(status="adoptable", tip=pet.tip).exclude(pk=pet.pk)
    if pet.varsta_aproximativa is not None:
        qs = qs.filter(varsta_aproximativa=pet.varsta_aproximativa)
    if pet.marime:
        qs = qs.filter(marime=pet.marime)
    return list(qs[:limit])


@receiver(pre_save, sender=Pet)
def _store_old_pet_status(sender, instance, **kwargs):
    """Salvează statusul vechi pe instance pentru post_save."""
    if instance.pk:
        try:
            instance._previous_status = Pet.objects.get(pk=instance.pk).status
        except Pet.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Pet)
def notify_wishlist_users_when_adopted(sender, instance, created, **kwargs):
    """Când un animal trece în status 'adopted', trimite email utilizatorilor care l-au pus la Te plac. Excepție: nu se aplică limita 7 zile."""
    previous = getattr(instance, "_previous_status", None)
    if previous == "adopted" or instance.status != "adopted":
        return
    favorites = PetFavorite.objects.filter(pet=instance, notified_adopted=False).select_related("user")
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    site_url = getattr(settings, "SITE_URL", "https://eu-adopt.ro").rstrip("/")
    recommended = _recommended_pets_for_adopted(instance, limit=3)
    rec_lines = []
    for p in recommended:
        path = reverse("pets_single", kwargs={"pk": p.pk})
        rec_lines.append(f"  • {p.nume} – {p.get_tip_display}, {p.rasa}: {site_url}{path}")
    rec_block = "\n".join(rec_lines) if rec_lines else ""

    subject = f"🎉 [EU Adopt] {instance.nume} a găsit familie!"
    body_base = (
        f"Bună ziua,\n\n"
        f"Vestea bună: sufletelul {instance.nume}, pe care l-ai marcat cu „Te plac”, a fost adoptat și a găsit familie!\n\n"
        f"Îți mulțumim pentru sprijinul acordat – fiecare „Te plac” contează.\n\n"
        f"Te invităm să vizitezi site-ul când ai chef, să vezi ce mai e nou – fără nicio obligație de adopție, pur și simplu de plăcere.\n\n"
    )
    if rec_block:
        body_base += f"Poate îți place și unul dintre acești prieteni:\n\n{rec_block}\n\n"
    body_base += f"Site: {site_url}\n\nCu drag,\nEchipa EU Adopt"

    html_base = (
        f"<p>Bună ziua,</p>"
        f"<p>Vestea bună: sufletelul <strong>{instance.nume}</strong>, pe care l-ai marcat cu „Te plac”, a fost adoptat și a găsit familie!</p>"
        f"<p>Îți mulțumim pentru sprijinul acordat.</p>"
        f"<p>Te invităm să vizitezi site-ul când ai chef – fără obligații, pur de plăcere.</p>"
    )
    if recommended:
        html_base += "<p>Poate îți place și:</p><ul>"
        for p in recommended:
            path = reverse("pets_single", kwargs={"pk": p.pk})
            html_base += f'<li><a href="{site_url}{path}">{p.nume}</a> – {p.get_tip_display}, {p.rasa}</li>'
        html_base += "</ul>"
    html_base += f"<p>Site: <a href=\"{site_url}\">{site_url}</a></p><p>Cu drag,<br>Echipa EU Adopt</p>"

    from django.utils import timezone
    now = timezone.now()
    for fav in favorites:
        try:
            user = fav.user
            email = (user.email or "").strip()
            if not email:
                continue
            send_wishlist_email(subject, body_base, email, from_email=from_email, html_body=html_base, user_for_unsubscribe=user)
            fav.notified_adopted = True
            fav.save(update_fields=["notified_adopted"])
            profile = getattr(user, "profile", None)
            if profile is not None:
                profile.last_wishlist_email_at = now
                profile.save(update_fields=["last_wishlist_email_at"])
        except Exception:
            pass


@receiver(post_save, sender=AdoptionRequest)
def send_email_to_owner_on_adoption_request_created(sender, instance, created, **kwargs):
    """
    La creare cerere adopție: trimite email către proprietor (owner/shelter/ong).
    După trimitere creează EmailDeliveryLog. Eșecul emailului NU blochează salvarea.
    """
    if not created:
        return
    from .adoption_platform import _recipient_email_for_pet
    try:
        from accounts.models import EmailDeliveryLog
    except ImportError:
        EmailDeliveryLog = None

    pet = getattr(instance, "pet", None)
    if not pet:
        logger.warning("send_email_to_owner_on_adoption_request_created: cerere fără pet, pk=%s", instance.pk)
        return

    to_email = _recipient_email_for_pet(pet)
    if not to_email:
        logger.warning("send_email_to_owner_on_adoption_request_created: niciun email pentru animal %s (pk=%s)", pet.nume, pet.pk)
        return

    subject = "Cerere nouă de adopție"
    adopter_name = (getattr(instance, "nume_complet", None) or "").strip() or "—"
    site_url = getattr(settings, "SITE_URL", "https://eu-adopt.ro").rstrip("/")
    try:
        admin_path = reverse("admin:anunturi_adoptionrequest_change", args=[instance.pk])
        admin_link = f"{site_url}{admin_path}" if not admin_path.startswith("http") else admin_path
    except Exception:
        admin_link = f"{site_url}/admin/anunturi/adoptionrequest/{instance.pk}/change/"

    body = (
        f"Bună ziua,\n\n"
        f"A fost înregistrată o cerere nouă de adopție.\n\n"
        f"Animal: {pet.nume}\n"
        f"Adoptator: {adopter_name}\n\n"
        f"Link către cerere în admin:\n{admin_link}\n\n"
        f"Cu stimă,\nEchipa EU Adopt"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    try:
        send_mail(
            subject,
            body,
            from_email,
            [to_email],
            fail_silently=False,
        )
        if EmailDeliveryLog:
            try:
                EmailDeliveryLog.objects.create(
                    user=instance.owner,
                    email_type="adoption_request_new",
                    status="sent",
                    to_email=to_email,
                    subject=subject,
                )
            except Exception:
                pass
        logger.info("Email cerere adopție trimis la %s pentru %s (cerere pk=%s)", to_email, pet.nume, instance.pk)
    except Exception as e:
        logger.exception("Trimitere email cerere adopție eșuată la %s: %s", to_email, e)
        if EmailDeliveryLog:
            try:
                EmailDeliveryLog.objects.create(
                    user=instance.owner,
                    email_type="adoption_request_new",
                    status="failed",
                    to_email=to_email,
                    subject=subject,
                    error_message=str(e),
                )
            except Exception:
                pass
