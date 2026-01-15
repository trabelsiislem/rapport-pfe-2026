from datetime import timedelta
from django.utils import timezone
import logging
import os

from .models import Appointment, AvailabilitySlot
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_appointment_email(appointment, action='created'):
    """Send email notifications to both customer and provider when an appointment is
    created or cancelled. action is 'created' or 'cancelled'."""
    subject = ''
    if action == 'created':
        subject = f'Confirmation de rendez-vous — {appointment.service_type or "Service"}'
        verb = 'confirmé'
    elif action == 'cancelled':
        subject = f'Annulation de rendez-vous — {appointment.service_type or "Service"}'
        verb = 'annulé'
    else:
        subject = f'Mise à jour rendez-vous — {appointment.service_type or "Service"}'
        verb = 'mis à jour'

    start = appointment.start.strftime('%Y-%m-%d %H:%M')
    end = appointment.end.strftime('%Y-%m-%d %H:%M')
    customer_name = getattr(appointment.customer, 'username', str(appointment.customer))
    provider_name = getattr(appointment.provider, 'name', str(appointment.provider))

    body = (
        f'Bonjour,\n\n'
        f'Le rendez-vous pour le service "{appointment.service_type}" a été {verb}.\n\n'
        f'Détails:\n'
        f'Client: {customer_name}\n'
        f'Prestataire: {provider_name}\n'
        f'Service: {appointment.service_type}\n'
        f'Début: {start}\n'
        f'Fin: {end}\n\n'
        f'Si vous n\'êtes pas l\'origine de cette action, contactez-nous.'
    )

    recipients = []
    # customer email
    cust_email = getattr(appointment.customer, 'email', None)
    if cust_email:
        recipients.append(cust_email)

    # provider email: prefer provider.email, fallback to linked user email
    prov_email = getattr(appointment.provider, 'email', None) or (getattr(appointment.provider.user, 'email', None) if getattr(appointment.provider, 'user', None) else None)
    if prov_email and prov_email not in recipients:
        recipients.append(prov_email)

    if not recipients:
        logger.info("No recipient emails found for appointment id=%s; skipping email", getattr(appointment, 'id', None))
        return False

    try:
        # Force the sender email to the requested address (can be overridden by SENDER_EMAIL env var)
        from_email = os.environ.get('SENDER_EMAIL', 'itrabelsi507@gmail.com')
        # Do not silence failures in dev — log them so the developer can see what went wrong.
        send_mail(subject, body, from_email, recipients, fail_silently=False)
        logger.info("Sent appointment email (action=%s) from %s to %s for appointment id=%s", action, from_email, recipients, getattr(appointment, 'id', None))
        return True
    except Exception:
        # Log the full exception traceback for debugging (SMTP auth, connection, TLS issues, etc.)
        logger.exception("Failed to send appointment email (action=%s) for appointment id=%s to %s", action, getattr(appointment, 'id', None), recipients)
        return False


def overlaps(start1, end1, start2, end2):
    """Return True if two intervals overlap."""
    return start1 < end2 and start2 < end1


def provider_has_conflict(provider, start, end, padding_before=0, padding_after=0):
    """Return True if provider has an appointment that conflicts with [start,end),
    taking into account padding (minutes).
    padding_before/after are integers (minutes).
    """
    padded_start = start - timedelta(minutes=padding_before)
    padded_end = end + timedelta(minutes=padding_after)
    qs = Appointment.objects.filter(provider=provider, status__in=['pending', 'confirmed'])
    return qs.filter(start__lt=padded_end, end__gt=padded_start).exists()


def appointment_within_availability(provider, start, end, padding_before=0, padding_after=0):
    """Return True if there exists an AvailabilitySlot for provider that fully contains
    the appointment interval after applying padding (i.e., slot.start <= start - padding_before
    and slot.end >= end + padding_after) and is not a blocking slot.
    """
    adj_start = start - timedelta(minutes=padding_before)
    adj_end = end + timedelta(minutes=padding_after)
    return AvailabilitySlot.objects.filter(provider=provider, is_block=False, start__lte=adj_start, end__gte=adj_end).exists()


def find_available_slots(provider, service_type, day, slot_length_minutes=None):
    """
    Find available start datetimes for a provider on a given day (date or datetime).

    day: date or datetime — we consider the 24h period of that day in UTC.
    slot_length_minutes: if None, use service_type.default_duration

    Returns list of (start, end) datetimes (UTC-aware)
    """
    if slot_length_minutes is None:
        slot_length_minutes = service_type.default_duration

    # padding for the service
    pad_before = service_type.padding_before or 0
    pad_after = service_type.padding_after or 0

    # normalize day to date
    if hasattr(day, 'date'):
        day_date = day.date()
    else:
        day_date = day

    tz = timezone.get_current_timezone()
    day_start = timezone.datetime(day_date.year, day_date.month, day_date.day, tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    slots = []
    avail_qs = AvailabilitySlot.objects.filter(provider=provider, end__gt=day_start, start__lt=day_end)
    step = timedelta(minutes=slot_length_minutes)

    for avail in avail_qs.order_by('start'):
        window_start = max(avail.start, day_start)
        window_end = min(avail.end, day_end)
        # skip blocked slots
        if avail.is_block:
            continue

        cursor = window_start
        while cursor + step <= window_end:
            candidate_start = cursor
            candidate_end = cursor + step

            # ensure the candidate plus padding stays within the availability window
            if (candidate_start - timedelta(minutes=pad_before)) < avail.start or (candidate_end + timedelta(minutes=pad_after)) > avail.end:
                cursor += step
                continue

            # check conflicts with existing appointments (consider padding)
            if not provider_has_conflict(provider, candidate_start, candidate_end, padding_before=pad_before, padding_after=pad_after):
                slots.append((candidate_start, candidate_end))
            cursor += step

    return slots
