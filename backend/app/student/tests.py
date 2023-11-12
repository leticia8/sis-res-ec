import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.gis.geos import GEOSGeometry
from django.urls import reverse
from residence.models.residence import Residence, Room, Bed, BedPrice, ResidenceType
from reservation.models.reservation import Reservation
from reservation.models.payment import Payment
from common.models import PaymentMethod, Zone, Sex, Address, Department
from student.models.student import Student
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class StudentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', first_name='Camila', last_name='Rodriguez', email='unestudiante@gmail.com', password='Unestudiante321')
        user_manager = User.objects.create_user(
            username='Un gestor', email='ungestor@gmail.com', password='Ungestor321')
        Group.objects.get_or_create(id=1, name='Manager')
        Group.objects.get_or_create(id=2, name='Student')
        my_group = Group.objects.get(name="Student")
        my_group.user_set.add(user_student)
        my_group2 = Group.objects.get(name="Manager")
        my_group2.user_set.add(user_manager)
        cls.api_client = APIClient()
        refresh = RefreshToken.for_user(user_manager)
        cls.api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        sex = Sex.objects.get(description="Mujer")
        dep = Department.objects.get(id=1)
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student, department=dep)
        cls.student = student1
        type = ResidenceType.objects.get(description="Mixta")
        Zone.objects.get(description='Cordón')
        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.1767115015472 -34.9022949556816)'), zone_id=1)
        residence1 = Residence.objects.create(id=1, name='Resi1', bussines_name='Una resi', rut='2121', tel='29002929',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type)
        room1 = Room.objects.create(name="aroom", residence=residence1)
        bed1 = Bed.objects.create(id=1, name='bed1', room=room1, status=3)
        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from='2021-12-04',
                                          date_until='2022-04-02', date_created=timezone.now(), status=3)
        pay_met = PaymentMethod.objects.get(pk=1)
        BedPrice.objects.create(price=12500, date_from='2020-11-22', bed=bed1)
        Payment.objects.create(amount=18400, year_month=202102, payment_date="2021-09-10",
                               status=3, payment_method=pay_met, reservation=res1)

    def test_student_detail_view(self):
        stud = Student.objects.get(document='11111111')
        url = reverse('student-detail', args=[stud.id])
        response = self.api_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['document'], '11111111')
        self.assertEqual(response.data[0]['user_first_name'], 'Camila')
        self.assertEqual(response.data[0]['user_last_name'], 'Rodriguez')
        self.assertEqual(
            response.data[0]['user_mail'], 'unestudiante@gmail.com')
        self.assertEqual(response.data[0]['birth_date'],
                         datetime.date(2000, 11, 12))
        self.assertEqual(response.data[0]['sex_desc'], 'Mujer')
        self.assertEqual(response.data[0]['medical_soc'], None)
        self.assertEqual(response.data[0]['dep_desc'], 'Montevideo')
        self.assertEqual(response.data[0]['allergies'], None)

    def test_student_list(self):
        url = reverse('student-list')
        response = self.api_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['user_first_name'], self.student.user.first_name)
        self.assertEqual(
            response.data[0]['user_last_name'], self.student.user.last_name)
        self.assertEqual(response.data[0]['document'], self.student.document)
        self.assertEqual(response.data[0]['sex_desc'],
                         self.student.sex.description)
