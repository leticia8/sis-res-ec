from collections import defaultdict
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Notification(models.Model):
    RESERVATION = 0
    PAYMENT = 1
    SERVICE = 2
    COMMENT = 3
    USER = 4
    NOTIFICATION_STATUS = (
        (RESERVATION, ('Reservation')),
        (PAYMENT, ('Payment')),
        (SERVICE, ('Service')),
        (COMMENT, ('Comment')),
        (USER, ('User')),
    )
    notification_status_dict = defaultdict(dict)
    for var, text in NOTIFICATION_STATUS:
        notification_status_dict[var] = text

    title = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    date_created = models.DateTimeField(default=None, blank=True, null=True)
    date_viewed = models.DateTimeField(default=None, blank=True, null=True)
    type = models.IntegerField(choices=NOTIFICATION_STATUS)
    link = models.URLField(max_length=400, default=None, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
