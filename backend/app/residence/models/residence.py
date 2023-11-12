from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from common.models import Address, Zone, PaymentMethod
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers

User = get_user_model()


class BedType(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=200)


class ResidenceType(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class Amenity(models.Model):
    id = models.IntegerField(primary_key=True, serialize=True, default=1)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class Residence(models.Model):
    name = models.CharField(max_length=100)
    bussines_name = models.CharField(max_length=100)
    rut = models.CharField(max_length=14)
    description = models.CharField(max_length=400, blank=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    tel = models.CharField(max_length=50)
    mail = models.EmailField(max_length=100)
    facebook = models.URLField(max_length=200)
    instagram = models.URLField(max_length=200)
    payment_method = models.ManyToManyField(
        PaymentMethod, db_table='residence_payment_methods_accepted')
    type = models.ForeignKey(ResidenceType, on_delete=models.CASCADE)
    amenity = models.ManyToManyField(
        Amenity, db_table='residence_residence_amenity')
    manager = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @property
    def main(self):
        return self.photo_set.filter(main=True).first()


class Room(models.Model):
    name = models.CharField(max_length=200)
    amenity = models.ManyToManyField(
        Amenity, db_table='residence_room_amenity')
    residence = models.ForeignKey(Residence, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @property
    def all_beds(self):
        return self.bed_set.filter(status=3).count()


class Bed(models.Model):
    INACTIVE = 0
    CANCELLED = 1
    PENDING = 2
    ACTIVE = 3
    STATUS = (
        (INACTIVE, ('Inactive')),
        (CANCELLED, ('Cancelled')),
        (PENDING, ('Pending')),
        (ACTIVE, ('Active')),
    )
    name = models.CharField(max_length=50, blank=True, null=True)
    status = models.IntegerField(choices=STATUS, default=ACTIVE)
    type = models.ForeignKey(
        BedType, on_delete=models.CASCADE, blank=True, null=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @property
    def actual_price(self):
        today = timezone.now()
        bed = self.bedprice_set.filter((Q(date_until__gte=today) | Q(
            date_until=None)), date_from__lte=today).first()
        if bed is not None:
            return bed.price
        else:
            return None

    def specific_price(self, date):
        try:
            bed_price = self.bedprice_set.filter((Q(date_until__gte=date) | Q(
                date_until__isnull=True)), date_from__lte=date).first()
            return bed_price.price
        except ObjectDoesNotExist:
            ("The object does not exist in DB")


class BedPrice(models.Model):
    price = models.DecimalField(default=0, max_digits=10, decimal_places=1)
    date_from = models.DateField()
    date_until = models.DateField(blank=True, null=True)
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.price)
