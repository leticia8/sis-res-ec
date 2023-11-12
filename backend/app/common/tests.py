from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.gis.geos import GEOSGeometry
from residence.models.residence import Residence, ResidenceType
from common.models import Sex, Address
from django.urls import reverse
from common.models import Sex, Message
from student.models.student import Student
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class CommonTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        cls.user_manager = user_manager
        cls.client = APIClient()
        sex = Sex.objects.get(description="Mujer")
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student = student1
        type = ResidenceType.objects.get(description="Mixta")
        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.1767115015472 -34.9022949556816)'), zone_id=1)
        residence1 = Residence.objects.create(id=1, name='Resi1', bussines_name='Una resi', rut='2121', tel='11111111',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type)
        cls.student_client = APIClient()
        cls.student_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(cls.student).access_token}')
        cls.manager_client = APIClient()
        cls.manager_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(cls.user_manager).access_token}')

    def test_message_list(self):
        url = reverse('message-list')
        data = {"message": "Me gustaría saber si tiene cocina",
                "to_mes": self.user_manager.id}
        response = self.student_client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.manager_client.get(url, format='json')
        final_res = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response)
        self.assertEqual(final_res[0]['other_user'], self.student.id)
        self.assertEqual(final_res[0]['conversation'][0]
                         ['message'], "Me gustaría saber si tiene cocina")

    def test_message_update(self):
        url = reverse('message-list')
        data = {"message": "Me gustaría saber si tiene cocina",
                "to_mes": self.user_manager.id}
        response = self.student_client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        id = Message.objects.get(from_mes_id=self.student.id).id
        data = {'id': id}
        response = self.manager_client.put(f'{url}{id}/', data, format='json')
        date_viewed = Message.objects.get(pk=id).date_viewed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(date_viewed)
