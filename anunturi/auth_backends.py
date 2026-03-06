"""
Backend de autentificare: acceptă atât username cât și email în câmpul „Utilizator / Email”.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticate cu username SAU email.
    Dacă valoarea conține '@', se caută după email (case-insensitive).
    Altfel se caută după username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        username = (username or "").strip()
        if not username:
            return None

        user = None
        if "@" in username:
            user = User.objects.filter(email__iexact=username).first()
        else:
            user = User.objects.filter(username__iexact=username).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
