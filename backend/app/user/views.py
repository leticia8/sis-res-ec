from rest_framework import viewsets
from reservation.models.reservation import Reservation
from reservation.views import create_notification
from residence.models.residence import Residence, Bed
from user.models import Notification
from user.serializers import TokenObtainPairSerializer, UserSerializer, NameRegistrationSerializer, NotificationSerializer, MailNotVerified
from student.models.student import Student
from common.views import check_permision, NotAuthorized
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from rest_auth.registration.views import RegisterView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView
from allauth.account.forms import EmailAwarePasswordResetTokenGenerator, UserTokenForm
from allauth.account.utils import user_pk_to_url_str, filter_users_by_email, url_str_to_user_pk, user_username
from allauth.utils import build_absolute_uri
from allauth.account.adapter import get_adapter
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView

User = get_user_model()


class CustomRegisterViewSet(RegisterView, viewsets.ModelViewSet):
    serializer_class = NameRegistrationSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        title = 'Actualización datos personales'
        description = 'Se solicita que actualice sus datos personales'
        mail = request.data.get('email')

        request.data.update({'username': mail})
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(email=mail)
        create_notification(title, description,
                            Notification.USER, user, user.id)
        custom_data = {"message": "The user has been created",
                       "status": status.HTTP_201_CREATED}
        response.data.update(custom_data)
        return response


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['GET'], url_path='check-role')
    def check_role(self, request):
        perm = check_permision(request.user)
        try:
            if perm == 1 or perm == 0:
                user = request.user
                result = self.check_role_method(user)
                return Response(data=result)
            else:
                raise NotAuthorized()
        except NotAuthorized:
            return Response(data={"detail": "You are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)

    @classmethod
    def check_role_method(cls, user):
        today = timezone.now()
        try:
            role = user.groups.first().name if user.groups is not None else None
            if role == "Student":
                student = Student.objects.filter(user=user).first()
                reservation = Reservation.objects.filter(date_until__gte=today, date_from__lte=today,
                                                        status=Bed.ACTIVE, student__user=user)
                residence = reservation.first().bed.room.residence.name if reservation else None

            elif role == "Manager":
                residence = Residence.objects.filter(
                    manager=user).values('name', 'id').first()
                student = None

            else:
                raise NotAuthorized()

            result = [
                {
                    'student_id': student.id if student else None,
                    'name': user.first_name,
                    'last_name': user.last_name,
                    'res': residence if residence else "No active association",
                    'role': role,
                }
            ]
            return result
        except NotAuthorized:
            return Response(data={"detail": "You are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, pk=None):
        username = self.get_object().username
        password = self.get_object().password
        email = self.get_object().email
        request.data.update(
            {'username': username, 'password': password, 'email': email})
        response = super().update(request)
        return response


class NameRegistrationView(RegisterView):
    serializer_class = NameRegistrationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.filter()
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                notifications = self.queryset.filter(
                    user=request.user, date_viewed__isnull=True)
            elif perm == 0:
                notifications = self.queryset.filter(user=request.user)
            else:
                raise NotAuthorized("user not authorized")
            serializer = NotificationSerializer(
                data=notifications, many=True)
            serializer.is_valid()
            return Response(data=serializer.data)
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=True, methods=['PUT'], url_path='read')
    def read(self, request, pk=None):
        perm = check_permision(request.user)
        today = timezone.now()
        try:
            if perm == 1 or perm == 0:
                instance = self.get_object()
                check_viewed = instance.date_viewed
                try:
                    if check_viewed is not None:
                        raise AlreadyViewed()
                    else:
                        instance.date_viewed = today
                        instance.save()
                    return Response()
                except AlreadyViewed:
                    return Response(data={"detail": "This notification has already be seen."},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)


class PasswordResetAPIView(APIView):
    def post(self, request):
        current_site = get_current_site(request)
        email = request.data.get('email')
        token_generator = EmailAwarePasswordResetTokenGenerator()

        for user in filter_users_by_email(email=email, is_active=True):

            temp_key = token_generator.make_token(user)

        # save it to the password reset model
        # password_reset = PasswordReset(user=user, temp_key=temp_key)
        # password_reset.save()

        # send the password reset email
        path = f'recuperacion/{user_pk_to_url_str(user)}-{temp_key}'
        # path = reverse(
        #     "account_reset_password_from_key",
        #     kwargs=dict(uidb36=user_pk_to_url_str(user), key=temp_key),
        # )
        url = build_absolute_uri(None, path)

        context = {
            "current_site": current_site,
            "user": user,
            "password_reset_url": url,
            "request": request,
        }

        context["username"] = user_username(user)
        get_adapter(request).send_mail(
            "account/email/password_reset_key", email, context
        )
        return Response()


class PasswordResetFromKeyAPIView(APIView):
    def post(self, request):
        User = get_user_model()
        key_from_request = request.data.get('key')
        uidb36, key = key_from_request.split('-', 1)
        token_form = UserTokenForm(data={"uidb36": uidb36, "key": key})
        if token_form.is_valid():
            pk = url_str_to_user_pk(uidb36)
            user = User.objects.get(pk=pk)
            get_adapter().set_password(user, request.data.get('new_password'))
            return Response()
        return Response(status=status.HTTP_401_UNAUTHORIZED)


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request=request, *args, **kwargs)
        except MailNotVerified:
            return Response(data={"detail": "The mail is not verified."}, status=status.HTTP_401_UNAUTHORIZED)


class AlreadyViewed(Exception):
    pass
