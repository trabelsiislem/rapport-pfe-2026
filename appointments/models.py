from django.db import models
from django.conf import settings
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('provider', 'Provider'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=30, blank=True)
    timezone = models.CharField(max_length=64, default='UTC')

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class ServiceType(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    default_duration = models.PositiveIntegerField(help_text='Duration in minutes', default=30)
    padding_before = models.PositiveIntegerField(default=0, help_text='Minutes before appointment')
    padding_after = models.PositiveIntegerField(default=0, help_text='Minutes after appointment')
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Provider(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    services = models.ManyToManyField(ServiceType, related_name='providers', blank=True)
    location = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class AvailabilitySlot(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='availability')
    start = models.DateTimeField()
    end = models.DateTimeField()
    is_block = models.BooleanField(default=False, help_text='If true, this slot blocks availability (e.g. vacation)')

    class Meta:
        ordering = ['provider', 'start']

    def __str__(self):
        return f"{self.provider.name}: {self.start.isoformat()} -> {self.end.isoformat()}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='appointments')
    service_type = models.ForeignKey(ServiceType, on_delete=models.SET_NULL, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start']
        indexes = [models.Index(fields=['provider', 'start'])]

    def __str__(self):
        return f"{self.service_type} for {self.customer} at {self.start.isoformat()}"

    def clean(self):
        # Basic validation: end must be after start
        if self.end <= self.start:
            from django.core.exceptions import ValidationError

            raise ValidationError('Appointment end must be after start')
