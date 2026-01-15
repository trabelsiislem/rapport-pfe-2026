from rest_framework import serializers
from django.utils import timezone

from .models import Appointment, Provider, ServiceType

from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already taken')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(username=validated_data['username'], email=validated_data.get('email',''))
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserProfileSerializer(serializers.Serializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False)
    role = serializers.CharField()
    phone = serializers.CharField(allow_blank=True, required=False)
    timezone = serializers.CharField(required=False)

    def update(self, instance, validated_data):
        # instance is UserProfile
        user_data = validated_data.get('user', {})
        if 'email' in user_data:
            instance.user.email = user_data['email']
            instance.user.save()

        for attr in ('role', 'phone', 'timezone'):
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()
        return instance

    def to_representation(self, instance):
        return {
            'username': instance.user.username,
            'email': instance.user.email,
            'role': instance.role,
            'phone': instance.phone,
            'timezone': instance.timezone,
        }


class AvailabilitySlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class AppointmentCreateSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(queryset=Provider.objects.all())
    service_type = serializers.PrimaryKeyRelatedField(queryset=ServiceType.objects.all())

    class Meta:
        model = Appointment
        # customer will be set from request.user
        fields = ('id', 'provider', 'service_type', 'start', 'end', 'status', 'notes')
        read_only_fields = ('id', 'status')

    def validate(self, data):
        # Basic validation: end after start
        start = data.get('start')
        end = data.get('end')
        if end <= start:
            raise serializers.ValidationError('End must be after start')

        provider = data.get('provider')
        service = data.get('service_type')
        # check provider availability/overlap
        from .utils import provider_has_conflict, appointment_within_availability

        # determine padding from service type
        pad_before = 0
        pad_after = 0
        if service is not None:
            pad_before = getattr(service, 'padding_before', 0) or 0
            pad_after = getattr(service, 'padding_after', 0) or 0

        # ensure the appointment lies within an availability slot (including padding)
        if not appointment_within_availability(provider, start, end, padding_before=pad_before, padding_after=pad_after):
            raise serializers.ValidationError('Requested time not within provider availability')

        if provider_has_conflict(provider, start, end, padding_before=pad_before, padding_after=pad_after):
            raise serializers.ValidationError('Provider not available at this time')

        return data

    def create(self, validated_data):
        # Create appointment marked as confirmed
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            customer = request.user
        else:
            customer = validated_data.get('customer')

        validated_data['status'] = 'confirmed'
        validated_data['customer'] = customer
        return super().create(validated_data)
