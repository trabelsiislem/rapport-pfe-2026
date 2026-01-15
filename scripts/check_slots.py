import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import datetime

django.setup()
from django.utils import timezone
from appointments.models import Provider
from appointments.utils import find_available_slots

p = Provider.objects.filter(pk=1).first()
if not p:
    print('No provider 1')
else:
    s = p.services.first()
    day = timezone.now().date()
    slots = find_available_slots(p, s, day)
    print('Found slots count:', len(slots))
    for st, en in slots:
        print(' -', st.isoformat(), '->', en.isoformat())
