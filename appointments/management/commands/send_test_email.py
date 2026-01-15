from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Send a test email using current Django email settings'

    def add_arguments(self, parser):
        parser.add_argument('recipient', nargs='?', help='Email address to send the test email to')

    def handle(self, *args, **options):
        recipient = options.get('recipient')
        if not recipient:
            raise CommandError('Please provide a recipient email address, e.g. ./manage.py send_test_email you@youremail.tld')

        subject = 'Test email from booking_app'
        message = 'This is a test email sent from the booking_app management command.'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'itrabelsi507@gmail.com')

        try:
            send_mail(subject, message, from_email, [recipient], fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f'Sent test email to {recipient} using {settings.EMAIL_BACKEND} (from={from_email})'))
        except Exception as exc:
            raise CommandError(f'Failed to send email: {exc}')
