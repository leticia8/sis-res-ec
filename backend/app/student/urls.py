from rest_framework import routers
from .views import StudentViewSet, TutorViewSet, StudentUpdateImageViewSet, RelationAPIView
from django.urls import path

router = routers.SimpleRouter()
router.register(r'student', StudentViewSet)
router.register(r'studentimage', StudentUpdateImageViewSet,
                basename='imageupdate')
router.register(r'tutor', TutorViewSet)
urlpatterns = router.urls + [
    path('relation/', RelationAPIView.as_view(),
         name='relation'),
]
