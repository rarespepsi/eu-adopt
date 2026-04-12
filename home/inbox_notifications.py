"""
Creare notificări pentru inbox-ul unificat (acțiuni finalizate pe site).
"""
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)

# Valori stabile `kind` (folosite în cod și eventual filtre admin)
KIND_ADOPTION_REQUEST_OWNER = "adoption_request_owner"
KIND_ADOPTION_REQUEST_ADOPTER = "adoption_request_adopter"
KIND_ADOPTION_ACCEPTED_ADOPTER = "adoption_accepted_adopter"
KIND_ADOPTION_REJECTED_ADOPTER = "adoption_rejected_adopter"
KIND_ADOPTION_SUPERSEDED_ADOPTER = "adoption_superseded_adopter"
KIND_ADOPTION_FINALIZED_OWNER = "adoption_finalized_owner"
KIND_ADOPTION_FINALIZED_ADOPTER = "adoption_finalized_adopter"
KIND_TRANSPORT_NO_TRANSPORTERS = "transport_no_transporters"
KIND_TRANSPORT_DISPATCH_OPEN = "transport_dispatch_open"
KIND_TRANSPORT_ASSIGNED_CLIENT = "transport_assigned_client"
KIND_TRANSPORT_ASSIGNED_OPERATOR = "transport_assigned_operator"
KIND_TRANSPORT_EXHAUSTED = "transport_exhausted"
KIND_TRANSPORT_EXPIRED = "transport_expired"
KIND_TRANSPORT_CANCELLED_USER = "transport_cancelled_user"
KIND_TRANSPORT_REOPENED = "transport_reopened"
KIND_TRANSPORT_COMPLETED = "transport_completed"
KIND_OFFER_CLAIM_BUYER = "offer_claim_buyer"
KIND_OFFER_CLAIM_COLLABORATOR = "offer_claim_collaborator"
KIND_PROMO_A2_PAID = "promo_a2_paid"
KIND_PUBLICITATE_PAID = "publicitate_paid"


def reverse_safe(name: str, *args: Any, **kwargs: Any) -> str:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return ""


def create_inbox_notification(
    user: AbstractBaseUser | AnonymousUser | None,
    kind: str,
    title: str,
    body: str = "",
    link_url: str = "",
    metadata: dict | None = None,
):
    """
    Persistă o notificare pentru utilizator. Ignoră utilizatori anonimi / fără pk.
    """
    if user is None or not getattr(user, "is_authenticated", False) or not getattr(user, "pk", None):
        return None
    from .models import UserInboxNotification

    try:
        return UserInboxNotification.objects.create(
            user_id=user.pk,
            kind=(kind or "misc")[:64],
            title=(title or "")[:200],
            body=(body or "")[:4000],
            link_url=(link_url or "")[:500],
            metadata=metadata if metadata is not None else {},
        )
    except Exception:
        logger.exception("create_inbox_notification kind=%s user=%s", kind, getattr(user, "pk", None))
        return None
