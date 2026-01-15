from django.urls import path
from . import views

# server-rendered frontend pages
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('services/', views.ServiceListView.as_view(), name='service-list'),
    path('providers/', views.ProvidersListView.as_view(), name='providers-list'),
    path('providers/<int:pk>/', views.ProviderDetailView.as_view(), name='provider-detail'),
    path('providers/<int:provider_id>/book/', views.ProviderBookingView.as_view(), name='provider-book'),
    path('my-appointments/', views.MyAppointmentsView.as_view(), name='my-appointments'),
    path('appointments/<int:pk>/cancel/', views.CancelAppointmentView.as_view(), name='appointment-cancel'),
]
