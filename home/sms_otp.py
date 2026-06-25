"""
OTP SMS via SMSAPI (https://www.smsapi.ro).

Când EUADOPT_SMS_OTP_ENABLED=0 (implicit): cod fix din SMS_OTP_DEV_CODE, fără trimitere SMS.
Când activ + token: cod aleator 6 cifre în cache, trimis prin API.
"""

from __future__ import annotations

import logging
import re
import secrets
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "euadopt:sms_otp:"


def is_sms_otp_enabled() -> bool:
    return bool(getattr(settings, "SMS_OTP_ENABLED", False))


def is_sms_otp_live() -> bool:
    """SMS real (API + token). Altfel rămâne modul dev cu cod fix din settings."""
    if not is_sms_otp_enabled():
        return False
    return bool(getattr(settings, "EUADOPT_SMSAPI_TOKEN", "").strip())


def sms_otp_template_context() -> dict[str, Any]:
    return {
        "sms_otp_live": is_sms_otp_live(),
        "sms_otp_dev_code": getattr(settings, "SMS_OTP_DEV_CODE", "528419"),
    }


def normalize_phone_digits(phone_country: str, phone: str) -> str:
    """Format SMSAPI: 407xxxxxxxx (fără +, spații)."""
    country = re.sub(r"\D", "", (phone_country or "+40").strip()) or "40"
    local = re.sub(r"\D", "", (phone or "").strip())
    if local.startswith("00"):
        local = local[2:]
    if local.startswith(country):
        return local
    if local.startswith("0"):
        local = local[1:]
    return f"{country}{local}"


def resolve_signup_phone_parts(signup_data: dict) -> tuple[str, str]:
    """
    PF: phone_country + phone.
    ONG / Colaborator / Adăpost: câmp unic ``telefon`` (ex. 07..., +40 ...).
    """
    role = (signup_data.get("role") or "pf").strip().lower()
    if role == "pf":
        return (
            (signup_data.get("phone_country") or "+40").strip() or "+40",
            (signup_data.get("phone") or "").strip(),
        )
    telefon = (signup_data.get("telefon") or "").strip()
    if telefon:
        parts = telefon.split(None, 1)
        if len(parts) == 2 and parts[0].startswith("+"):
            return parts[0], parts[1]
        if telefon.startswith("0"):
            return "+40", telefon
        return "+40", telefon
    return (
        (signup_data.get("phone_country") or "+40").strip() or "+40",
        (signup_data.get("phone") or "").strip(),
    )


def _phone_digits_valid(to_digits: str) -> bool:
    digits = re.sub(r"\D", "", to_digits or "")
    return len(digits) >= 10


def _session_cache_key(request, suffix: str) -> str:
    if not request.session.session_key:
        request.session.save()
    return f"{_CACHE_PREFIX}{suffix}:{request.session.session_key}"


def _edit_cache_key(user_pk: int) -> str:
    return f"{_CACHE_PREFIX}edit:{user_pk}"


def _otp_ttl() -> int:
    return int(getattr(settings, "SMS_OTP_TTL_SECONDS", 300))


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _dev_code() -> str:
    return str(getattr(settings, "SMS_OTP_DEV_CODE", "528419"))


def verify_sms_code(
    entered: str,
    *,
    request=None,
    purpose: str = "signup",
    user_pk: int | None = None,
) -> tuple[bool, str]:
    code = (entered or "").strip()
    if not code:
        return False, "Introdu codul primit prin SMS."

    if not is_sms_otp_live():
        if code == _dev_code():
            return True, ""
        return False, f"Cod invalid. Folosește {_dev_code()} pentru verificare."

    if purpose == "edit" and user_pk is not None:
        cache_key = _edit_cache_key(user_pk)
    elif request is not None:
        cache_key = _session_cache_key(request, purpose)
    else:
        return False, "Cod invalid sau expirat."

    expected = cache.get(cache_key)
    if not expected or code != expected:
        return False, "Cod invalid sau expirat. Poți cere retrimitere."

    cache.delete(cache_key)
    return True, ""


def _build_message(otp: str) -> str:
    return f"Codul tau EU-Adopt: {otp}. Valabil 5 minute."


def _send_sms(to_digits: str, message: str) -> tuple[bool, str | None]:
    token = getattr(settings, "EUADOPT_SMSAPI_TOKEN", "").strip()
    if not token:
        logger.warning("SMS OTP enabled but EUADOPT_SMSAPI_TOKEN is empty")
        return False, "Trimiterea SMS nu este configurată. Contactează suportul."

    sender = getattr(settings, "EUADOPT_SMSAPI_SENDER", "").strip() or "EU-Adopt"

    try:
        from smsapi.client import Client
        from smsapi.exception import SmsApiException
    except ImportError:
        logger.exception("smsapi-client not installed")
        return False, "Serviciul SMS nu este disponibil momentan."

    api_url = getattr(settings, "EUADOPT_SMSAPI_API_URL", "https://api.smsapi.ro/").strip()
    if not api_url.endswith("/"):
        api_url += "/"

    client = Client(api_url, access_token=token)
    try:
        results = client.sms.send(to=to_digits, message=message, from_=sender)
        for result in results:
            if getattr(result, "error", None):
                logger.error("SMSAPI error for %s: %s", to_digits[-4:], result.error)
                return False, "Nu am putut trimite SMS-ul. Încearcă din nou."
        logger.info("SMS OTP sent to ...%s", to_digits[-4:])
        return True, None
    except SmsApiException as exc:
        logger.exception("SMSAPI exception: %s", exc)
        return False, "Nu am putut trimite SMS-ul. Încearcă din nou."
    except Exception:
        logger.exception("Unexpected SMS send failure")
        return False, "Nu am putut trimite SMS-ul. Încearcă din nou."


def _store_and_send(request, purpose: str, phone_country: str, phone: str, *, force_new: bool) -> tuple[bool, str | None]:
    if not is_sms_otp_live():
        return True, None

    cache_key = _session_cache_key(request, purpose)
    if not force_new and cache.get(cache_key):
        return True, None

    to_digits = normalize_phone_digits(phone_country, phone)
    if not _phone_digits_valid(to_digits):
        logger.warning("SMS OTP invalid phone digits: ...%s", (to_digits or "")[-4:])
        return False, "Număr de telefon invalid. Verifică formatul (ex. 07xxxxxxxx) și încearcă din nou."

    otp = _generate_code()
    cache.set(cache_key, otp, _otp_ttl())
    ok, err = _send_sms(to_digits, _build_message(otp))
    if not ok:
        cache.delete(cache_key)
    return ok, err


def ensure_signup_otp_sent(request, signup_data: dict) -> tuple[bool, str | None]:
    phone_country, phone = resolve_signup_phone_parts(signup_data)
    return _store_and_send(
        request,
        "signup",
        phone_country,
        phone,
        force_new=False,
    )


def resend_signup_otp(request, signup_data: dict) -> tuple[bool, str | None]:
    phone_country, phone = resolve_signup_phone_parts(signup_data)
    return _store_and_send(
        request,
        "signup",
        phone_country,
        phone,
        force_new=True,
    )


def ensure_edit_otp_sent(request, edit_data: dict, user_pk: int) -> tuple[bool, str | None]:
    if not is_sms_otp_live():
        return True, None

    cache_key = _edit_cache_key(user_pk)
    if cache.get(cache_key):
        return True, None

    otp = _generate_code()
    cache.set(cache_key, otp, _otp_ttl())
    to_digits = normalize_phone_digits(
        edit_data.get("phone_country", "+40"),
        edit_data.get("phone", ""),
    )
    ok, err = _send_sms(to_digits, _build_message(otp))
    if not ok:
        cache.delete(cache_key)
    return ok, err
