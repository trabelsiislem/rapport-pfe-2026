#!/usr/bin/env python3
"""Send a test email using the Django settings in this project.
Usage: ./env/bin/python scripts/send_test_email.py recipient@example.tld
Or set TEST_EMAIL_RECIPIENT environment variable.
"""
import os
import sys

recipient = None
if len(sys.argv) > 1:
    recipient = sys.argv[1]
else:
    recipient = os.environ.get('TEST_EMAIL_RECIPIENT')

if not recipient:
    print('Usage: send_test_email.py recipient@example.tld or set TEST_EMAIL_RECIPIENT')
    sys.exit(2)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Ensure project root is on sys.path so Django settings module can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()

from django.conf import settings
from django.core.mail import send_mail

print('Using EMAIL_BACKEND=', settings.EMAIL_BACKEND)
print('DEFAULT_FROM_EMAIL=', settings.DEFAULT_FROM_EMAIL)

try:
    send_mail('Test email from booking_app', 'Ceci est un test envoyé depuis send_test_email.py', settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
    print('Sent test email to', recipient)
    sys.exit(0)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
