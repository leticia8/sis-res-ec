from django.db import models
from common.models import Department, Sex
from datetime import date
from django.utils import timezone
from django.contrib.auth import get_user_model


User = get_user_model()


MOTHER_RELATION = 1
FATHER_RELATION = 2
RELATIVE_RELATION = 3
TUTOR_RELATION = 4
OTHER_RELATION = 5

RELATION_CHOICES = (
    (1, 'Mother'),
    (2, 'Father'),
    (3, 'Other relative'),
    (4, 'Tutor not relative'),
    (5, 'Other person'))


def check_student_exists(user_id):
    stud = Student.objects.filter(user__id=user_id)
    if stud.count() == 1:
        return stud
    else:
        return None


def profile_path(instance, filename):
    today = timezone.now()
    id = instance.id
    ext = instance.image.name.split('.')[-1]
    return 'media/profiles/{0}_{1}.{2}'.format(id, today, ext)


class Student(models.Model):
    URUGUAYAN = 1
    PASSPORT = 2
    DOCUMENT = (
        (URUGUAYAN, ('UY')),
        (PASSPORT, ('PA')),
    )
    document = models.CharField(max_length=200, unique=True)
    document_type = models.IntegerField(choices=DOCUMENT)
    image = models.ImageField(
        upload_to=profile_path, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    cel = models.CharField(max_length=20, blank=True, null=True)
    medical_soc = models.CharField(max_length=200, blank=True, null=True)
    allergies = models.CharField(max_length=200, blank=True, null=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, blank=True, null=True, default=None)
    sex = models.ForeignKey(Sex, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.document

    @property
    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day)
                                                    < (self.birth_date.month, self.birth_date.day))


class Tutor(models.Model):
    name = models.CharField(max_length=200)
    relation = models.IntegerField(choices=RELATION_CHOICES)
    cel = models.CharField(max_length=20)
    address = models.CharField(max_length=200, null=True, blank=True)
    data = models.CharField(max_length=200, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def get_relation(self, obj):
        return obj.get_relation_display()
