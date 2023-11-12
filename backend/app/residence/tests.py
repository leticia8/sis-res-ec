from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.gis.geos import GEOSGeometry
from django.urls import reverse
from residence.models.residence import Residence, Room, Bed, BedPrice, ResidenceType
from reservation.models.reservation import Reservation
from reservation.models.payment import Payment
from common.models import PaymentMethod, Zone, Sex, Address
from student.models.student import Student
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import datetime
User = get_user_model()


class ResidenceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
        user_manager = User.objects.create_user(
            username='Un gestor', email='ungestor@gmail.com', password='Ungestor321')
        user_manager2 = User.objects.create_user(
            username='Dos gestor', email='dosgestor@gmail.com', password='Dosgestor321')
        Group.objects.get_or_create(id=1, name='Manager')
        Group.objects.get_or_create(id=2, name='Student')
        my_group = Group.objects.get(name="Student")
        my_group.user_set.add(user_student)
        my_group2 = Group.objects.get(name="Manager")
        my_group2.user_set.add(user_manager)
        my_group2.user_set.add(user_manager2)
        cls.api_client = APIClient()
        refresh = RefreshToken.for_user(user_manager)
        cls.api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        sex = Sex.objects.get(description="Mujer")
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student = student1
        type = ResidenceType.objects.get(description="Mixta")
        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.1767115015472 -34.9022949556816)'), zone_id=1)
        residence1 = Residence.objects.create(id=1, name='Resi1', bussines_name='Una resi', rut='2121', tel='11111111',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type)
        residence2 = Residence.objects.create(id=2, name='Resi2', bussines_name='Dos resi', rut='2222', tel='22222222',
                                              mail='dosresi@gmail.com', address=address, manager=user_manager2, type=type)
        cls.res = residence1
        room1 = Room.objects.create(name="aroom", residence=residence1)
        bed1 = Bed.objects.create(id=1, name='bed1', room=room1, status=3)
        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from='2021-12-04',
                                          date_until='2022-04-02', date_created=timezone.now(), status=3)
        pay_met = PaymentMethod.objects.get(pk=1)
        BedPrice.objects.create(price=12500, date_from='2020-11-22', bed=bed1)
        Payment.objects.create(amount=18400, year_month=202102, payment_date="2021-09-10",
                               status=3, payment_method=pay_met, reservation=res1)

    def test_residence_list(self):
        url = reverse('residence-list')
        response = self.api_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual((response.data[0]['name']), 'Resi1')
        self.assertEqual((response.data[1]['name']), 'Resi2')
    
    def test_residence_detail_view(self):
        url = reverse('residence-detail', args=[1])
        response = self.api_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Resi1')
        self.assertEqual(response.data['mail'], 'unaresi@gmail.com')
        self.assertEqual(response.data['tel'], '11111111')
        self.assertEqual(response.data['address']
                         ['zone']['description'], 'Ciudad Vieja')
        self.assertEqual(response.data['address']['street'], 'Miguelete')
        self.assertEqual(list(response.data.keys()), [
                         'name', 'description', 'type_desc','manager','address', 'amenities', 'rating', 'photos', 'rooms', 'mail', 'tel', 'facebook', 'instagram'])

    def test_filter_residence_max(self):
        url = reverse('residence-filter-residence')
        data = {'zone_id': 1, 'max_price': 17000}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data[0]['id'])

    def test_filter_residence_min(self):
        url = reverse('residence-filter-residence')
        data = {'min_price': 18000}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_filter_residence_min_max(self):
        url = reverse('residence-filter-residence')
        data = {'min_price': 11000, 'max_price': 18000}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual('Resi1', response.data[0]['name'])

    def test_filter_residence_zone(self):
        url = reverse('residence-filter-residence')
        data = {'zone_id': 1}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual('Resi1', response.data[0]['name'])

    def test_filter_distance(self):
        url = reverse('residence-filter-distance')
        data = {'centerid': 36, 'distance': 150}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual('Resi1', response.data[0]['name'])

    def test_total_payments(self):
        url = reverse('residence-total-payments', args=[1])
        data = {'yearmonth_from': 202101, 'yearmonth_until': 202112}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(18400), response.data[0]['all_payments'])

    def month_income(self, request, pk=None):
        url = reverse('residence-month-income', args=[1])
        data = {'yearmonth_from': 202101, 'yearmonth_until': 202112}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(18400), response.data[0]['all_payments'])


class RoomTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
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
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student = student1
        type = ResidenceType.objects.get(description="Mixta")
        zone = Zone.objects.get(description='Cordón')
        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.1767115015472 -34.9022949556816)'), zone_id=1)
        residence1 = Residence.objects.create(id=1, name='Resi1', bussines_name='Una resi', rut='2121', tel='11111111',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type)
        cls.res = residence1
        room1 = Room.objects.create(name="aroom", residence=residence1)
        room2 = Room.objects.create(name="secondroom", residence=residence1)
        bed1 = Bed.objects.create(id=1, name='bed1', room=room1, status=3)
        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from='2021-12-04',
                                          date_until='2022-04-02', date_created=timezone.now(), status=3)
        pay_met = PaymentMethod.objects.get(pk=1)
        BedPrice.objects.create(price=12500, date_from='2020-11-22', bed=bed1)
        Payment.objects.create(amount=18400, year_month=202102, payment_date="2021-09-10",
                               status=3, payment_method=pay_met, reservation=res1)

    def test_room_detail_view(self):
        url = reverse('residence-detail', args=[1])
        response = self.api_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['rooms']), 2)
        self.assertEqual(response.data['rooms'][0]['name'], 'aroom')
        self.assertEqual(response.data['rooms'][0]['all_beds'], 1)
        self.assertEqual(len(response.data['rooms'][0]['amenities']), 0)
        self.assertEqual(list(response.data['rooms'][0].keys()), [
                         'id', 'name', 'amenities', 'all_beds', 'photos'])


class BedTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
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
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        type = ResidenceType.objects.get(description="Mixta")
        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.1767115015472 -34.9022949556816)'), zone_id=1)
        residence1 = Residence.objects.create(id=1, name='Resi1', bussines_name='Una resi', rut='2121',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type)
        cls.res = residence1
        room1 = Room.objects.create(name="aroom", residence=residence1)
        bed1 = Bed.objects.create(id=1, name='bed1', room=room1, status=3)
        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from='2021-12-04',
                                          date_until='2022-04-02', date_created=timezone.now(), status=3)
        pay_met = PaymentMethod.objects.get(pk=1)
        BedPrice.objects.create(price=12500, date_from='2020-11-22', bed=bed1)
        Payment.objects.create(amount=18400, year_month=202102, payment_date="2021-09-10",
                               status=3, payment_method=pay_met, reservation=res1)

    def test_check_availability(self):
        url = reverse('residence-check-availability', args=[1])
        data = {'date_from': self.today.date().isoformat(), 'date_until': (self.today + timezone.timedelta(days=130)).date().isoformat()}
        response = self.api_client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[1]['free_beds'], 0)

    def test_price(self):
        url = reverse('bed-price', args=[1])
        data = {'future_bedprice': 15600, "date_until_prev_price": "2021-08-24",
                "date_from_act_price": "2021-08-25"}
        request = self.api_client.put(url, data, format='json')
        a_bed = Bed.objects.get(pk=1).actual_price
        query = BedPrice.objects.filter(bed=1)
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        self.assertEqual(float(15912), a_bed)
        self.assertEquals(query.first().date_until, datetime.date(2021, 8, 24))
        self.assertEquals(query.last().date_from, datetime.date(2021, 8, 25))
