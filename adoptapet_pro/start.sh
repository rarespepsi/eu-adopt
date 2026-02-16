#!/usr/bin/env bash
# Pornește serviciul - rulează migrate și seed înainte de gunicorn
set -e
python manage.py migrate --noinput
python manage.py seed_demo_pets
exec gunicorn platforma.wsgi:application
