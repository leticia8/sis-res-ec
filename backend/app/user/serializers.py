from django.contrib.auth.models import Group
from rest_framework import serializers
from reservation.views import create_notification
from user.models import Notification
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_auth.registration.serializers import RegisterSerializer
from django.utils import timezone
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer

User = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email']

    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email']
        )
        users_group = Group.objects.get(name='Student')
        user.groups.set([users_group])
        title = 'Actualización datos personales'
        description = 'Se solicita que actualice sus datos personales'
        create_notification(title, description,
                            Notification.USER, user, user.id)
        return user


class UserManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password',  'first_name', 'last_name', 'email']

    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email']
        )
        users_group = Group.objects.get(name='Manager')
        user.groups.set([users_group])
        return user


class NameRegistrationSerializer(RegisterSerializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'password',  'first_name', 'last_name', 'email']

    def custom_signup(self, request, user):
        today = timezone.now()
        user.first_name = self.validated_data.get('first_name', '')
        user.last_name = self.validated_data.get('last_name', '')
        users_group = Group.objects.get(name='Student')
        user.groups.set([users_group])
        user.save(update_fields=['first_name', 'last_name'])

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', '')
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        return user


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        verified = False
        for emailaddress in user.emailaddress_set.all():
            verified |= emailaddress.verified
        if not verified:
            raise MailNotVerified('Email not verified')
        return super().get_token(user)


class MailNotVerified(Exception):
    pass
