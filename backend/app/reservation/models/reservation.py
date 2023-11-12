from django.db import models
from student.models.student import Student
from residence.models.residence import Bed
from residence.models.serviceoffered import ServiceOffered
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


def contract_path(instance, filename):
    today = timezone.now()
    id = instance.id
    ext = instance.contract.name.split('.')[-1]
    return 'media/contracts/{0}_{1}.{2}'.format(id, today, ext)


class Reservation(models.Model):
    reservation_number = models.CharField(
        max_length=10, unique=True, blank=False)
    date_from = models.DateField('date_from', default=None)
    date_until = models.DateField('date_until', default=None)
    status = models.IntegerField(choices=Bed.STATUS, default=Bed.PENDING)
    date_cancelled = models.DateTimeField(blank=True, null=True, default=None)
    date_finalized = models.DateTimeField(blank=True, null=True, default=None)
    date_created = models.DateTimeField('date_created', default=timezone.now)
    observations = models.CharField(max_length=200, null=True, default=None)
    reject_reason = models.CharField(
        max_length=400, default=None, blank=True, null=True)
    contract = models.FileField(
        upload_to=contract_path, default=None, blank=True, null=True)
    bed = models.ForeignKey(
        Bed, on_delete=models.CASCADE, blank=True, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    service = models.ManyToManyField(
        ServiceOffered, through='ServiceConsumed', related_name="serviceconsumed")


class Comment (models.Model):
    score = models.DecimalField(
        max_digits=2, blank=True, null=True, decimal_places=1)
    review = models.CharField(
        max_length=200, blank=True, null=True, default=None)
    date_created = models.DateTimeField(blank=True, null=True, default=None)
    status = models.IntegerField(choices=Bed.STATUS, default=Bed.PENDING)
    reject_reason = models.CharField(max_length=400, null=True, default=None)
    date_rejected = models.DateTimeField(null=True, default=None)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.score <= 5 and self.score >= 1:
            super().save(*args, **kwargs)
        else:
            raise InvalidRange('The score range must be between 1 and 5')


class ServiceConsumed(models.Model):
    date_created = models.DateField(blank=True, default=timezone.now)
    amount = models.DecimalField(default=0, max_digits=10, decimal_places=1)
    payment_date = models.DateField(null=True, default=None)
    date_cancelled = models.DateField(blank=True, default=None, null=True)
    observations = models.CharField(max_length=400, null=True, default=None)
    service = models.ForeignKey(
        ServiceOffered, on_delete=models.CASCADE, related_name="service_consumed")
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)


class InvalidRange(Exception):
    pass
