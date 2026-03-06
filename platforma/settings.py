"""
Django settings for platforma project.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Încarcă variabile din .env (dacă există)
load_dotenv(BASE_DIR / ".env")

# Environment variables for production (Render)
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-#!76zwfds$te^uzw+*ubc7z6wypgng6&74x91u@-$n@5m7=lsv')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')

# Site public: False = vizitatorii văd „Site în pregătire”; True = site normal.
# Când ești gata: setează SITE_PUBLIC=True în .env sau pe Render (variabilă de mediu).
SITE_PUBLIC = os.environ.get('SITE_PUBLIC', 'False').lower() in ('1', 'true', 'yes')

# Link secret ca doar tu să vezi site-ul când e în pregătire.
# Setează MAINTENANCE_SECRET în .env (ex: un cuvânt lung, greu de ghicit).
# Pe laptop deschizi o dată: https://site.ro/acces-pregatire/ACEST_CUVANT/
# Doar browserul acela va avea acces (cookie 30 zile).
MAINTENANCE_SECRET = os.environ.get('MAINTENANCE_SECRET', '')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'anunturi',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'platforma.maintenance.MaintenanceMiddleware',
    'anunturi.referral_middleware.ReferralTrackingMiddleware',
]

ROOT_URLCONF = 'platforma.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'anunturi.context_processors.navbar_counters_context',
                'anunturi.context_processors.wishlist_context',
                'anunturi.context_processors.sidebar_boxes',
            ],
        },
    },
]

WSGI_APPLICATION = 'platforma.wsgi.application'


# Database
_sqlite_path = (BASE_DIR / "db.sqlite3").resolve().as_posix()
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{_sqlite_path}',
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Media files (uploads - poze animale etc.)
MEDIA_URL = 'media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT') or ('/tmp/media' if os.environ.get('RENDER') else str(BASE_DIR / 'media'))

# CSRF - pentru domeniul Render
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'https://*.onrender.com').split(',')

# Auth: login cu username SAU email (câmpul „Utilizator / Email”)
AUTHENTICATION_BACKENDS = [
    "anunturi.auth_backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Auth redirects
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
# După logout redirecționăm la Acasă ca vizitator (folosim logout_view care face redirect la home).
LOGOUT_REDIRECT_URL = "home"

# ========== EMAIL (SMTP Gmail) ==========
# Trimitere email reală: bun venit, cereri adopție, wishlist, etc.
# Parola NU este parola Gmail normală – trebuie creată „Parolă pentru aplicații” din Google Account.
# Vezi GHID_EMAIL.md sau https://myaccount.google.com/apppasswords
SITE_URL = os.environ.get('SITE_URL', 'https://eu-adopt.ro')

_use_smtp = os.environ.get('EMAIL_HOST') or os.environ.get('EMAIL_HOST_PASSWORD')
if _use_smtp:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'contact.euadopt@gmail.com')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'EU-Adopt <contact.euadopt@gmail.com>')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'contact.euadopt@gmail.com')

# Email de test pentru /debug/send-test-email/ (opțional; altfel folosește ?to= în URL)
DEBUG_TEST_EMAIL = os.environ.get('DEBUG_TEST_EMAIL', '')

# ========== SMS (verificare telefon) ==========
# În development: cod fix acceptat la validare (ex: 111111). Lăsat gol în producție.
SMS_DEV_CODE = os.environ.get('SMS_DEV_CODE', '111111' if DEBUG else '')

# ========== PF – limite cereri adopție ==========
# Max cereri noi per persoană fizică în ultimele 24h (anti-spam).
PF_DAILY_ADOPTION_REQUEST_LIMIT = int(os.environ.get('PF_DAILY_ADOPTION_REQUEST_LIMIT', '5'))

# ========== Siguranță (producție) ==========
# Când DEBUG=False, header-ele și cookie-urile se pun corect pentru HTTPS.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'