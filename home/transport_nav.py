"""Helpers for Transport back-navigation (sursa=transport*)."""

from urllib.parse import urlencode

from django.urls import reverse


def is_transport_sursa(sursa: str) -> bool:
    s = (sursa or "").strip().lower()
    return s in ("transport", "transport_hub") or s.startswith("transport_")


def transport_sursa_context(sursa: str) -> dict:
    sursa = (sursa or "").strip()[:96]
    from_transport = is_transport_sursa(sursa)
    ctx = {
        "from_transport": from_transport,
        "transport_query_sursa": sursa,
    }
    if from_transport:
        ctx["donatii_back_href"] = reverse("transport")
        ctx["donatii_back_label"] = "← Înapoi la Transport"
    else:
        qs = ("?" + urlencode({"sursa": sursa})) if sursa else ""
        ctx["donatii_back_href"] = reverse("donatii_generale") + qs
        ctx["donatii_back_label"] = "← Înapoi la Donații"
    return ctx
