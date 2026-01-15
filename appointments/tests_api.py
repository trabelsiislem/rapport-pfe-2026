from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date
from rest_framework.test import APIClient

from .models import Provider, ServiceType, Appointment
from django.contrib.auth import get_user_model

User = get_user_model()


class ApiBookingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='cust', password='pass')
        self.client.force_authenticate(user=self.user)
        self.provider_user = User.objects.create_user(username='prov', password='pass')
        self.provider = Provider.objects.create(user=self.provider_user, name='Dr API')
        self.service = ServiceType.objects.create(name='Consult', default_duration=30)
        self.provider.services.add(self.service)

        tz = timezone.get_current_timezone()
        today = date.today()
        start = timezone.datetime(today.year, today.month, today.day, 9, 0, tzinfo=tz)
        end = start + timedelta(hours=8)
        from .models import AvailabilitySlot
        AvailabilitySlot.objects.create(provider=self.provider, start=start, end=end)

    def test_get_availability(self):
        url = reverse('provider-availability', kwargs={'provider_id': self.provider.pk})
        resp = self.client.get(url, {'date': date.today().isoformat()})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(isinstance(data, list))

    def test_create_appointment(self):
        tz = timezone.get_current_timezone()
        today = date.today()
        appt_start = timezone.datetime(today.year, today.month, today.day, 10, 0, tzinfo=tz)
        appt_end = appt_start + timedelta(minutes=30)
        url = reverse('appointment-create')
        resp = self.client.post(url, {
            'provider': self.provider.pk,
            'service_type': self.service.pk,
            'start': appt_start.isoformat(),
            'end': appt_end.isoformat(),
            'notes': 'Test booking'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Appointment.objects.filter(provider=self.provider, start=appt_start).exists())
