from django.contrib import admin
from . import models


@admin.register(models.UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'timezone')


@admin.register(models.ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_duration', 'active')


@admin.register(models.Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_active')
    filter_horizontal = ('services',)


@admin.register(models.AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('provider', 'start', 'end', 'is_block')


@admin.register(models.Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'customer', 'provider', 'start', 'end', 'status')
    list_filter = ('status', 'provider')
    search_fields = ('customer__username', 'provider__name', 'service_type__name')
    actions = ['mark_confirmed', 'mark_cancelled', 'mark_completed']

    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f"{updated} rendez-vous marqués comme confirmés")

    mark_confirmed.short_description = 'Marquer sélection comme Confirmés'

    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"{updated} rendez-vous marqués comme annulés")

    mark_cancelled.short_description = 'Marquer sélection comme Annulés'

    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} rendez-vous marqués comme complétés")

    mark_completed.short_description = 'Marquer sélection comme Complétés'
