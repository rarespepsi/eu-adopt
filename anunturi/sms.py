"""
Trimitere SMS pentru verificarea bonității (cod 6 cifre).
În producție: setați SMS_BACKEND în settings (ex. 'twilio') și configurați API key-urile.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms_verification(phone: str, code: str) -> bool:
    """
    Trimite SMS cu codul de verificare la numărul dat.
    Returnează True dacă trimiterea a reușit (sau în mod stub), False la eroare.
    """
    phone = (phone or "").strip()
    if not phone:
        return False
    message = f"Cod Adopt a Pet: {code}. Introdu codul in casutele de pe site pentru a finaliza."
    backend = getattr(settings, "SMS_BACKEND", "console")
    if backend == "console":
        logger.info("SMS (stub) catre %s: %s", phone, message)
        print(f"[SMS stub] To: {phone} | {message}")  # noqa: T201
        return True
    if backend == "twilio":
        return _send_via_twilio(phone, message)
    logger.warning("SMS_BACKEND necunoscut: %s. Folosesc stub.", backend)
    logger.info("SMS (stub) catre %s: %s", phone, message)
    return True


def _send_via_twilio(phone: str, message: str) -> bool:
    """Exemplu integrare Twilio. Setează TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM în settings."""
    try:
        from twilio.rest import Client
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        from_number = getattr(settings, "TWILIO_FROM", None)
        if not all([account_sid, auth_token, from_number]):
            logger.warning("Twilio: lipsesc setarile. Folosesc stub.")
            logger.info("SMS (stub) catre %s: %s", phone, message)
            return True
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_number, to=phone)
        return True
    except Exception as e:
        logger.exception("Eroare trimitere SMS Twilio: %s", e)
        return False
