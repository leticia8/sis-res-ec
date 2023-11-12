from django.db import models
from reservation.models.reservation import Reservation
from residence.models.residence import PaymentMethod, Bed
from common.views import NoActiveAssociation
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
User = get_user_model()


def year_month_validate(value):
    monthes = list(range(1, 12))
    if (value % 100) not in monthes:
        raise serializers.ValidationError('Yearmonth must be between 1 and 5')


def payment_path(instance, filename):
    today = timezone.now()
    id = instance.id
    ext = instance.file.name.split('.')[-1]
    return 'media/payments/{0}_{1}.{2}'.format(id, today, ext)


class Payment(models.Model):
    status = models.IntegerField(choices=Bed.STATUS, default=Bed.PENDING)
    amount = models.DecimalField(decimal_places=1, default=0, max_digits=10)
    year_month = models.IntegerField(
        validators=[year_month_validate])
    payment_date = models.DateField()
    observations = models.CharField(
        max_length=200, default=None, blank=True, null=True)
    reject_reason = models.CharField(
        max_length=400, default=None, blank=True, null=True)
    date_status = models.DateField(default=None, blank=True, null=True)
    file = models.FileField(blank=True, null=True,
                            default=None, upload_to=payment_path)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        resulta = Reservation.objects.filter(
            status=3, student__user=self.reservation.student.user).distinct('id').count()
        if resulta == 0:
            raise NoActiveAssociation(
                'There is no an existing association but it is required')
        else:
            super().save(*args, **kwargs)
