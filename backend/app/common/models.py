from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()


class Zone(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=200)
    photo = models.ImageField(blank=True, null=True, upload_to='media/zones')

    def __str__(self):
        return self.description

    @property
    def url(self):
        if self.photo:
            return self.photo.url
        return None


class Address (models.Model):
    street = models.CharField(max_length=200)
    number = models.IntegerField()
    apartment = models.CharField(max_length=8, blank=True, null=True)
    location = models.PointField(
        geography=True, default=Point(0.0, 0.0), blank=True, null=True)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)

    @property
    def longitude(self):
        return self.location.x

    @property
    def latitude(self):
        return self.location.y


class Institute(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=100)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)


class Sex(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=40)

    def __str__(self):
        return self.description


class Department(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=40)

    def __str__(self):
        return self.description


class PaymentMethod(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description


class ServiceType(models.Model):
    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=40)

    def __str__(self):
        return self.description


class Message(models.Model):
    message = models.CharField(max_length=400)
    from_mes = models.ForeignKey(User, on_delete=models.CASCADE, related_name='from_mes')
    to_mes = models.ForeignKey(User, on_delete=models.CASCADE, related_name='to_mes')
    date_created = models.DateTimeField(default=timezone.now)
    date_viewed = models.DateTimeField(default=None, blank=True, null=True)
