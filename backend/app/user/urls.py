from rest_framework import routers

from user.views import UserViewSet, NotificationViewSet, PasswordResetFromKeyAPIView
from django.contrib.auth import get_user_model
from django.urls import re_path

User = get_user_model()

router = routers.DefaultRouter()
router.register(r'user', UserViewSet)
router.register(r'notification', NotificationViewSet)

urlpatterns = router.urls + [
    re_path(
        r"^password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        PasswordResetFromKeyAPIView.as_view(),
        name="account_reset_password_from_key",
    ),
]
