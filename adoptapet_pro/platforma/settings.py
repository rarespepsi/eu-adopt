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

# Auth redirects
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
# După logout redirecționăm la login (nu la home), ca în mod „site în pregătire”
# utilizatorul să vadă login, nu ecranul 503.
LOGOUT_REDIRECT_URL = "login"

# ========== EMAIL ==========
# Folosit la: cereri adopție (→ ONG), validare adopție, follow-up post-adopție.
# Vezi GHID_EMAIL.md pentru setup Gmail / SendGrid / etc.
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@eu-adopt.ro')

if os.environ.get('EMAIL_HOST'):
    # Producție: trimite email real (setează variabile în Render)
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
else:
    # Local / fără config: afișează emailurile în consolă (nu trimite)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'