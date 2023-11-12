from django.db import models
from .residence import Residence, Room
from datetime import date
from django.utils import timezone


def photo_path(instance, filename):
    today = timezone.now()
    id = instance.id
    ext = instance.image.name.split('.')[-1]
    return 'media/residence/{0}_{1}.{2}'.format(id, today, ext)


class Photo(models.Model):
    alt_text = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='media/residence')
    main = models.BooleanField(default=False)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, blank=True, null=True)
    residence = models.ForeignKey(
        Residence, on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs):
        if (self.room is None and self.residence is None) or (self.room is not None and self.residence is not None):
            raise PhotoHasTwoFks(
                'Two foreign keys for room and residence are not allowed')

        else:
            super().save(*args, **kwargs)


class PhotoHasTwoFks(Exception):
    pass
