from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointments'
    verbose_name = 'Appointments'

    def ready(self):
        # Import signals to ensure UserProfile is created on User creation
        try:
            import appointments.signals  # noqa: F401
        except Exception:
            pass
