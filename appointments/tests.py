from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date

from .models import Provider, ServiceType, Appointment, AvailabilitySlot
from .utils import find_available_slots


User = get_user_model()


class BookingLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cust', password='pass')
        self.provider_user = User.objects.create_user(username='prov', password='pass')
        self.provider = Provider.objects.create(user=self.provider_user, name='Dr Test')
        self.service = ServiceType.objects.create(name='Consult', default_duration=30)
        self.provider.services.add(self.service)

        # availability: today 09:00-17:00
        tz = timezone.get_current_timezone()
        today = date.today()
        start = timezone.datetime(today.year, today.month, today.day, 9, 0, tzinfo=tz)
        end = start + timedelta(hours=8)
        AvailabilitySlot.objects.create(provider=self.provider, start=start, end=end)

    def test_find_slots_no_conflict(self):
        today = date.today()
        slots = find_available_slots(self.provider, self.service, today)
        self.assertTrue(len(slots) >= 1)

    def test_conflicting_appointment_removed(self):
        tz = timezone.get_current_timezone()
        today = date.today()
        appt_start = timezone.datetime(today.year, today.month, today.day, 10, 0, tzinfo=tz)
        appt_end = appt_start + timedelta(minutes=30)
        Appointment.objects.create(customer=self.user, provider=self.provider, service_type=self.service, start=appt_start, end=appt_end, status='confirmed')

        slots = find_available_slots(self.provider, self.service, today)
        # ensure the 10:00 slot isn't listed
        starts = [s[0] for s in slots]
        self.assertNotIn(appt_start, starts)
