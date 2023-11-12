from rest_framework import routers
from residence.views import ResidenceViewSet, PhotoAllViewSet, PaymentMethodViewSet, BedViewSet, RoomViewSet, ResTypeViewSet, ResidenceRegistrationAPIView, BedTypeViewSet
from django.urls import path

router = routers.SimpleRouter()
router.register(r'residence', ResidenceViewSet)
router.register(r'photo', PhotoAllViewSet)
router.register(r'paymentmethod', PaymentMethodViewSet)
router.register(r'bed', BedViewSet)
router.register(r'room', RoomViewSet)
router.register(r'restype', ResTypeViewSet)
router.register(r'bedtype', BedTypeViewSet)


urlpatterns = router.urls + [path('register',
                                  ResidenceRegistrationAPIView.as_view(), name='register'),
                             ]
