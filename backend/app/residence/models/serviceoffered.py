from django.db import models
from residence.models.residence import Residence
from common.models import ServiceType


class ServiceOffered(models.Model):
    residence = models.ForeignKey(Residence, on_delete=models.CASCADE)
    service = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
