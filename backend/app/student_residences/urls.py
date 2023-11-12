"""student_residences URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from user.views import TokenObtainPairView, CustomRegisterViewSet, PasswordResetAPIView, PasswordResetFromKeyAPIView

from allauth.account.views import ConfirmEmailView
from django.contrib import admin
from django.conf.urls import include
from django.urls import include, path, re_path
from rest_framework_simplejwt import views as jwt_views
from django.contrib.auth import get_user_model

User = get_user_model()


urlpatterns = [
    path('', include('student.urls')),
    path('', include('residence.urls')),
    path('', include('reservation.urls')),
    path('', include('user.urls')),
    path('', include('common.urls')),
    path('admin/', admin.site.urls),
    re_path(r'^accounts/password/reset/',
            PasswordResetAPIView.as_view(), name='account_reset_password'),
    re_path(r'^accounts/password/reset-from-key/',
            PasswordResetFromKeyAPIView.as_view(), name='account_reset_from_key'),
    re_path(r'^accounts/', include('allauth.urls')),
    re_path(r'^rest-auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$',
            ConfirmEmailView.as_view(), name='account_confirm_email'),
    path('api/token/', TokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(),
         name='token_refresh'),
    path('rest-auth/', include('rest_auth.urls')),
    path('rest-auth/registration/', include('rest_auth.registration.urls')),
    path(r'custom/registration/',
         CustomRegisterViewSet.as_view({'post': 'create'}), name='CustomRegister'),


]
