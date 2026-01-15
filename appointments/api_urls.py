from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('providers/<int:provider_id>/availability/', views.ProviderAvailabilityView.as_view(), name='provider-availability'),
    path('appointments/', views.AppointmentCreateView.as_view(), name='appointment-create'),
    path('accounts/register/', views.RegisterView.as_view(), name='account-register'),
    path('accounts/token/', obtain_auth_token, name='api-token-auth'),
    path('accounts/profile/', views.ProfileAPIView.as_view(), name='api-account-profile'),
]
