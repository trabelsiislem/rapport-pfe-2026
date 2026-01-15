import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from appointments.models import Provider, ServiceType, AvailabilitySlot

p = Provider.objects.filter(pk=1).first()
if not p:
    print('No provider with pk=1 found')
else:
    s = p.services.first()
    if not s:
        s = ServiceType.objects.create(name='Test Service', default_duration=30)
        p.services.add(s)
    # create a slot today 09:00-17:00 with the current timezone
    start = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=8)
    slot = AvailabilitySlot.objects.create(provider=p, start=start, end=end)
    print('Created slot:', slot.pk, slot.start, slot.end)
