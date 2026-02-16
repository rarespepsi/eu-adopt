#!/usr/bin/env bash
# Build script for Render
set -o errexit
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py seed_demo_pets
python manage.py collectstatic --noinput
