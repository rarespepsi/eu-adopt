"""
Date publice de contact EU-Adopt (telefon site + WhatsApp).

Nu pune tokenuri aici. Doar cifre / URL-uri publice.
"""
from __future__ import annotations

# Vanity: +40 73 EUADOPT (E=3 U=8 A=2 D=3 O=6 P=7 T=8)
EUADOPT_PUBLIC_PHONE_E164 = "+40733823678"
EUADOPT_PUBLIC_PHONE_DIGITS = "40733823678"
EUADOPT_PUBLIC_PHONE_DISPLAY = "+40 73 EUADOPT"
EUADOPT_WHATSAPP_URL = f"https://wa.me/{EUADOPT_PUBLIC_PHONE_DIGITS}"
EUADOPT_PUBLIC_PHONE_TEL_HREF = f"tel:{EUADOPT_PUBLIC_PHONE_E164}"


def public_contact_context() -> dict[str, str]:
    return {
        "euadopt_phone_e164": EUADOPT_PUBLIC_PHONE_E164,
        "euadopt_phone_display": EUADOPT_PUBLIC_PHONE_DISPLAY,
        "euadopt_phone_tel": EUADOPT_PUBLIC_PHONE_TEL_HREF,
        "euadopt_whatsapp_url": EUADOPT_WHATSAPP_URL,
    }
