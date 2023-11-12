from rest_framework import routers
from .views import ServiceConsumedViewSet, ReservationViewSet, ServiceViewSet, PaymentViewSet, CommentViewSet, PaymentReceiptViewSet, ReservationUploadContractViewSet, ServiceConsumedViewSet

router = routers.SimpleRouter()
router.register(r'reservation', ReservationViewSet, 'reservation')
router.register(r'reservationuploadcontract', ReservationUploadContractViewSet, 'uploadcontract')
router.register(r'payment', PaymentViewSet, 'payment')
router.register(r'paymentreceipt', PaymentReceiptViewSet, 'paymentreceipt')
router.register(r'comment', CommentViewSet)
router.register(r'serviceoffered', ServiceViewSet)
router.register(r'serviceconsumed', ServiceConsumedViewSet)
urlpatterns = router.urls
