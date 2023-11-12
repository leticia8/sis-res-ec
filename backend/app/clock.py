import django
from apscheduler.schedulers.blocking import BlockingScheduler
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_residences.settings')

django.setup()
from reservation.models.reservation import Reservation


sched = BlockingScheduler()


@sched.scheduled_job('cron')
def scheduled_job():
    from django.utils import timezone
    today = timezone.now()
    results = Reservation.objects.filter(
        date_until__lt=today, status__range=(2, 3))
    for result in results:
        if result.status == 3:
            result.status = 0
        elif result.status == 2:
            result.status = 1
            result.date_cancelled = today
            result.reject_reason = 'Cancelled by the system'
        result.save()


sched.start()
