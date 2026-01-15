#!/usr/bin/env python3
"""Bootstrap local development: migrate and create a superuser if none exists.
Usage: ./env/bin/python scripts/bootstrap_local.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model

print('Running migrations...')
call_command('migrate', interactive=False)

User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found — creating default superuser admin / admin (password: admin)')
    User.objects.create_superuser('admin', 'itrabelsi507@gmail.com', 'admin')
    print('Created superuser: username=admin password=admin')
else:
    print('Superuser already exists; skipping creation.')

print('\nBootstrap complete. You can run the dev server:')
print('./env/bin/python manage.py runserver 127.0.0.1:8000')
