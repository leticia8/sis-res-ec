from rest_framework import routers
from common.views import ZoneViewSet, InstituteViewSet, SexViewSet, DepartmentViewSet, NotificationAPIView, MessageViewSet
from django.urls import path

router = routers.SimpleRouter()
router.register(r'zone', ZoneViewSet)
router.register(r'institute', InstituteViewSet)
router.register(r'sex', SexViewSet)
router.register(r'department', DepartmentViewSet)
router.register(r'message', MessageViewSet)
urlpatterns = router.urls + [
    path('notification-codes/', NotificationAPIView.as_view(),
         name='notification'),
]
