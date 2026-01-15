from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import Provider, ServiceType, Appointment
from .serializers import AvailabilitySlotSerializer, AppointmentCreateSerializer
from .utils import find_available_slots, send_appointment_email
from .serializers import RegisterSerializer, UserSerializer
from rest_framework.permissions import AllowAny
from .serializers import UserProfileSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django import forms
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist
from .models import UserProfile
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone as dj_timezone
from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from .utils import find_available_slots


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ensure a UserProfile exists for this user (create on-demand)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        # allow partial updates (client may send only one or two fields)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(UserProfileSerializer(profile).data)


class ProfileForm(forms.Form):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False)
    timezone = forms.CharField(required=False)


@method_decorator(login_required, name='dispatch')
class ProfileView(APIView):
    # simple server-rendered profile edit page
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = ProfileForm(initial={'email': request.user.email, 'phone': profile.phone, 'timezone': profile.timezone})
        return render(request, 'appointments/profile.html', {'form': form, 'profile': profile})

    def post(self, request):
        form = ProfileForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            phone = form.cleaned_data.get('phone')
            timezone = form.cleaned_data.get('timezone')
            user = request.user
            if email is not None:
                user.email = email
                user.save()
            profile = user.userprofile
            if phone is not None:
                profile.phone = phone
            if timezone:
                profile.timezone = timezone
            profile.save()
            return redirect('account-profile-page')
        return render(request, 'appointments/profile.html', {'form': form})


class ProviderAvailabilityView(APIView):
    def get(self, request, provider_id):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'detail': 'date query parameter required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            day = timezone.datetime.fromisoformat(date_str)
        except Exception:
            # fallback to parsing date only
            try:
                parts = [int(p) for p in date_str.split('-')]
                day = timezone.datetime(parts[0], parts[1], parts[2])
            except Exception:
                return Response({'detail': 'invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        provider = get_object_or_404(Provider, pk=provider_id, is_active=True)
        # default to the first service if not provided
        service_pk = request.query_params.get('service')
        if service_pk:
            service = get_object_or_404(ServiceType, pk=service_pk)
        else:
            service = provider.services.first()
            if not service:
                return Response([], status=status.HTTP_200_OK)

        slots = find_available_slots(provider, service, day)
        data = [{'start': s.isoformat(), 'end': e.isoformat()} for s, e in slots]
        return Response(data)


from rest_framework.permissions import IsAuthenticated


class AppointmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AppointmentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Use a transaction and select_for_update on provider to reduce race conditions
        provider = serializer.validated_data['provider']
        with transaction.atomic():
            # lock provider row
            Provider.objects.select_for_update().get(pk=provider.pk)
            # double-check conflicts
            start = serializer.validated_data['start']
            end = serializer.validated_data['end']
            overlapping = Appointment.objects.select_for_update().filter(provider=provider, status__in=['pending','confirmed'], start__lt=end, end__gt=start).exists()
            if overlapping:
                return Response({'detail': 'Time slot taken'}, status=status.HTTP_409_CONFLICT)

            appointment = serializer.save()
            # send confirmation emails to customer and provider (best-effort)
            try:
                send_appointment_email(appointment, action='created')
            except Exception:
                pass
        return Response(AppointmentCreateSerializer(appointment).data, status=status.HTTP_201_CREATED)


class ServiceListView(ListView):
    model = ServiceType
    template_name = 'appointments/service_list.html'
    context_object_name = 'services'


class ProviderDetailView(DetailView):
    model = Provider
    template_name = 'appointments/provider_detail.html'
    context_object_name = 'provider'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # default to today
        qdate = self.request.GET.get('date')
        try:
            if qdate:
                day = dj_timezone.datetime.fromisoformat(qdate).date()
            else:
                day = date.today()
        except Exception:
            day = date.today()

        # choose service (first by default)
        service_pk = self.request.GET.get('service')
        if service_pk:
            try:
                service = ServiceType.objects.get(pk=service_pk)
            except ServiceType.DoesNotExist:
                service = self.object.services.first()
        else:
            service = self.object.services.first()

        slots = []
        if service:
            slots = find_available_slots(self.object, service, day)

        ctx.update({'slots': slots, 'selected_date': day, 'selected_service': service})
        return ctx


class ProviderBookingView(LoginRequiredMixin, View):
    def post(self, request, provider_id):
        provider = get_object_or_404(Provider, pk=provider_id)
        service_pk = request.POST.get('service')
        start_iso = request.POST.get('start')
        end_iso = request.POST.get('end')

        try:
            service = ServiceType.objects.get(pk=service_pk)
        except Exception:
            messages.error(request, 'Service invalide')
            return redirect('provider-detail', pk=provider_id)

        try:
            start = dj_timezone.datetime.fromisoformat(start_iso)
            end = dj_timezone.datetime.fromisoformat(end_iso)
        except Exception:
            messages.error(request, 'Format de date invalide')
            return redirect('provider-detail', pk=provider_id)

        # verify within availability and no conflict
        from .utils import provider_has_conflict, appointment_within_availability
        pad_before = service.padding_before or 0
        pad_after = service.padding_after or 0

        if not appointment_within_availability(provider, start, end, padding_before=pad_before, padding_after=pad_after):
            messages.error(request, 'Le créneau sélectionné n\'est pas disponible chez le prestataire')
            return redirect('provider-detail', pk=provider_id)

        if provider_has_conflict(provider, start, end, padding_before=pad_before, padding_after=pad_after):
            messages.error(request, 'Le créneau est déjà pris')
            return redirect('provider-detail', pk=provider_id)

        # create appointment
        appt = Appointment.objects.create(customer=request.user, provider=provider, service_type=service, start=start, end=end, status='confirmed')
        messages.success(request, 'Rendez-vous confirmé')
        return redirect('provider-detail', pk=provider_id)


class ProvidersListView(ListView):
    model = Provider
    template_name = 'appointments/providers_list.html'
    context_object_name = 'providers'

    def get_queryset(self):
        qs = Provider.objects.filter(is_active=True)
        service_pk = self.request.GET.get('service')
        if service_pk:
            qs = qs.filter(services__pk=service_pk)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        service_pk = self.request.GET.get('service')
        service = None
        if service_pk:
            try:
                service = ServiceType.objects.get(pk=service_pk)
            except ServiceType.DoesNotExist:
                service = None
        ctx['selected_service'] = service
        return ctx


class ContactForm(forms.Form):
    name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)


class HomeView(ListView):
    """Homepage showing banner, stats, sample services and providers and a contact form."""
    model = ServiceType
    template_name = 'appointments/home.html'
    context_object_name = 'services'

    def get_queryset(self):
        # return up to 6 services to showcase
        return ServiceType.objects.filter(active=True)[:6]

    def get(self, request, *args, **kwargs):
        # prepare context with stats and providers
        services_qs = self.get_queryset()
        providers_qs = Provider.objects.filter(is_active=True)[:6]
        services_count = ServiceType.objects.count()
        providers_count = Provider.objects.filter(is_active=True).count()
        appointments_count = Appointment.objects.count()

        form = ContactForm()
        context = {
            'services': services_qs,
            'providers': providers_qs,
            'services_count': services_count,
            'providers_count': providers_count,
            'appointments_count': appointments_count,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        services_qs = self.get_queryset()
        providers_qs = Provider.objects.filter(is_active=True)[:6]
        services_count = ServiceType.objects.count()
        providers_count = Provider.objects.filter(is_active=True).count()
        appointments_count = Appointment.objects.count()

        if form.is_valid():
            # For now, store nothing - show a success message. Sending email can be added later.
            messages.success(request, 'Merci — votre message a été reçu. Nous vous répondrons bientôt.')
            return redirect('home')

        context = {
            'services': services_qs,
            'providers': providers_qs,
            'services_count': services_count,
            'providers_count': providers_count,
            'appointments_count': appointments_count,
            'form': form,
        }
        return render(request, self.template_name, context)


class MyAppointmentsView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'appointments/my_appointments.html'
    context_object_name = 'appointments'

    def get_queryset(self):
        return Appointment.objects.filter(customer=self.request.user).order_by('start')


class CancelAppointmentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            appt = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            raise Http404()

        if appt.customer != request.user:
            messages.error(request, 'Vous ne pouvez pas annuler ce rendez-vous')
            return redirect('my-appointments')

        appt.status = 'cancelled'
        appt.save()
        # notify both parties about cancellation (best-effort)
        try:
            send_appointment_email(appt, action='cancelled')
        except Exception:
            pass
        messages.success(request, 'Rendez-vous annulé')
        return redirect('my-appointments')
