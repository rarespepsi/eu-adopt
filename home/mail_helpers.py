"""Helper-e minime pentru emailuri transmise către utilizatori."""


def email_subject_for_user(username: str | None, subject: str) -> str:
    """
    Prefixează subiectul cu [username] destinatarului (același inbox pe mai multe conturi).
    """
    u = (username or "").strip() or "?"
    base = (subject or "").strip()
    return f"[{u}] {base}"
