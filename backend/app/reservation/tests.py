
from django.contrib.auth.models import Group
from student.models.student import Student
from common.models import Sex, Address, PaymentMethod
from residence.models.residence import Residence, Room, Bed, BedPrice, ResidenceType
from reservation.models.reservation import Reservation, Comment
from reservation.models.payment import Payment
from user.models import Notification
from rest_framework import status
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from reservation import views
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.core import mail
User = get_user_model()


class ReservationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
        user_student2 = User.objects.create_user(
            username='Dos estudiante', email='dosestudiante@gmail.com', password='Dosestudiante321')
        user_student3 = User.objects.create_user(
            username='Tres estudiante', email='tresestudiante@gmail.com', password='Tresestudiante321')

        Group.objects.get_or_create(id=1, name='Student')
        my_group = Group.objects.get(id=1)
        my_group.user_set.add(user_student)
        my_group.user_set.add(user_student2)
        my_group.user_set.add(user_student3)

        user_manager = User.objects.create_user(
            username='Un gestor', email='ungestor@gmail.com', password='Ungestor321')
        cls.user_manager = user_manager

        cls.user_student2 = user_student2
        cls.user_student3 = user_student3

        Group.objects.get_or_create(id=2, name='Manager')
        my_group = Group.objects.get(id=2)
        my_group.user_set.add(user_manager)

        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.175840915813 -34.89271547922357)'), zone_id=1)
        type1 = ResidenceType.objects.get(pk=1)
        residence1 = Residence.objects.create(name='Resi1', bussines_name='Una resi', rut='2121',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type1)
        room1 = Room.objects.create(name="aroom", residence=residence1)
        bed1 = Bed.objects.create(name='bed1', room=room1)
        cls.bed1 = bed1
        bed2 = Bed.objects.create(name='bed2', room=room1)
        bed3 = Bed.objects.create(name='bed3', room=room1)
        cls.bed3 = bed3
        BedPrice.objects.create(price=8500, date_from='2020-11-22', bed=bed1)
        BedPrice.objects.create(price=9500, date_from='2020-11-22', bed=bed2)
        BedPrice.objects.create(price=10500, date_from='2020-11-02', bed=bed3)
        sex = Sex.objects.get(pk=1)
        pay_met = PaymentMethod.objects.get(pk=1)
        cls.pay_met = pay_met

        student1 = Student.objects.create(
            document='222222222', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student = student1

        student2 = Student.objects.create(
            document='1111111', document_type=1, birth_date='1999-04-12', sex=sex, user=user_student2)
        cls.student2 = student2

        student3 = Student.objects.create(
            document='78106599', document_type=1, birth_date='2004-03-22', sex=sex, user=user_student3)
        cls.student3 = student3

        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from=today,
                                          date_until=today + timezone.timedelta(days=30), date_created=today, status=3)
        cls.res = res1

        res2 = Reservation.objects.create(reservation_number='BBBB', student=student1, bed=bed2, date_from=today + timezone.timedelta(days=31),
                                          date_until=today + timezone.timedelta(days=130), date_created=cls.today, status=2)
        cls.res2 = res2

        res3 = Reservation.objects.create(reservation_number='CCCC', student=student3, bed=bed3, date_from=today + timezone.timedelta(days=31),
                                          date_until=today + timezone.timedelta(days=130), date_created=cls.today, status=2)
        cls.res3 = res3

        comm = Comment.objects.create(
            score=3, review='MALISIMO', date_created=today, status=3, reservation_id=res1.id)
        cls.comm = comm

        cls.student_client = APIClient()
        cls.student_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student).access_token}')
        cls.student_client2 = APIClient()
        cls.student_client2.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student2).access_token}')
        cls.manager_client = APIClient()
        cls.manager_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_manager).access_token}')

    def test_check_previous_association(self):
        final_response = views.check_previous_association(
            self.student, self.res.id)
        self.assertEqual(0, final_response)

    def test_obtain_reservation_data(self):
        reservations = [self.res]
        response = views.obtain_reservation_data(reservations)
        self.assertEqual(response[0]['reservation_number'], 'AAAA')
        self.assertEqual(response[0]['status'], 3)
        self.assertEqual(response[0]['residence']['name'], 'Resi1')
        self.assertEqual(response[0]['residence']['bed']['price'], float(8500))

    # Testing the reservation number format
    def test_reservation_number_created(self):
        reservation_number = views.create_reservation_number()
        self.assertEqual(len(reservation_number), 10)

    # Can't access to the list of pending reservation when logged in as a student
    def test_pending_approve_permissions(self):
        url = reverse('reservation-pending-approve')
        response = self.student_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # Creating a reservation from student user
    def test_create_reservation_student(self):
        url = reverse('reservation-list')
        data = {"bed": self.bed1.id, "date_from": self.today.date().isoformat(), "date_until": (
            self.today + timezone.timedelta(days=130)).date().isoformat()}
        response = self.student_client2.post(url, data, format="json")
        res = Reservation.objects.filter(student=self.student2)
        self.assertIsNotNone(res)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Error when trying to create a reservation when a previous association exists
    def test_create_reservation_error(self):
        Reservation.objects.create(reservation_number='DDDDD', student=self.student, bed=self.bed3, date_from=self.today + timezone.timedelta(days=31),
                                   date_until=self.today + timezone.timedelta(days=130), date_created=self.today, status=3)
        url = reverse('reservation-list')
        data = {"bed": self.bed1.id, "date_from": self.today.date().isoformat(
        ), "date_until": (self.today + timezone.timedelta(days=130)).date().isoformat()}
        response = self.student_client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['detail'], "There is a previous association for this student.")

    # Creating a reservation from a manager user
    def test_create_reservation_manager(self):
        url = reverse('reservation-list')
        data = {"student": self.student2.id, "bed": self.bed1.id, "date_from": (self.today + + timezone.timedelta(
            days=331)).date().isoformat(), "date_until": (self.today + timezone.timedelta(days=430)).date().isoformat()}
        response = self.manager_client.post(url, data, format="json")
        res = Reservation.objects.filter(student=self.student2)
        self.assertIsNotNone(res)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Test a notification is created after reservation is created
    def test_notification(self):
        url = reverse('reservation-list')
        data = {"bed": self.bed1.id, "date_from": (self.today + timezone.timedelta(days=230)).date(
        ).isoformat(), "date_until": (self.today + timezone.timedelta(days=230)).date().isoformat()}
        response1 = self.student_client.post(url, data, format="json")
        url = reverse('message-list')
        response = self.manager_client.get(url, format='json')
        notif = Notification.objects.get(user=self.user_manager)
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, 'Reserva creada')
        self.assertAlmostEquals(notif.type, 0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ReservationStatusTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
        user_student2 = User.objects.create_user(
            username='Dos estudiante', email='dosestudiante@gmail.com', password='Dosestudiante321')
        Group.objects.get_or_create(id=1, name='Student')
        my_group = Group.objects.get(id=1)
        my_group.user_set.add(user_student)
        my_group.user_set.add(user_student2)
        user_manager = User.objects.create_user(
            username='Un gestor', email='ungestor@gmail.com', password='Ungestor321')
        user_manager2 = User.objects.create_user(
            username='Dos gestor', email='dosgestor@gmail.com', password='Dosgestor321')
        cls.user_manager = user_manager
        cls.user_manager2 = user_manager2
        Group.objects.get_or_create(id=2, name='Manager')
        my_group = Group.objects.get(id=2)
        my_group.user_set.add(user_manager)
        my_group.user_set.add(user_manager2)

        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.175840915813 -34.89271547922357)'), zone_id=1)
        type1 = ResidenceType.objects.get(pk=1)
        residence1 = Residence.objects.create(name='Resi1', bussines_name='Una resi', rut='2121',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type1)
        room1 = Room.objects.create(name="aroom", residence=residence1)
        bed1 = Bed.objects.create(name='bed1', room=room1)
        bed2 = Bed.objects.create(name='bed2', room=room1)
        bed3 = Bed.objects.create(name='bed3', room=room1)
        cls.bed3 = bed3
        BedPrice.objects.create(price=8500, date_from=cls.today, bed=bed1)
        BedPrice.objects.create(price=9500, date_from='2020-11-22', bed=bed2)
        BedPrice.objects.create(price=10500, date_from='2020-11-02', bed=bed3)
        sex = Sex.objects.get(pk=1)
        pay_met = PaymentMethod.objects.get(pk=1)
        cls.pay_met = pay_met
        student1 = Student.objects.create(
            document='22222222', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student = student1
        student2 = Student.objects.create(
            document='1111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student2 = student2
        student3 = Student.objects.create(
            document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)

        cls.student3 = student3
        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from=today,
                                          date_until=today + timezone.timedelta(days=30), date_created=timezone.now(), status=3)
        cls.res = res1
        res2 = Reservation.objects.create(reservation_number='BBBB', student=student1, bed=bed2, date_from=today + timezone.timedelta(days=32),
                                          date_until=today + timezone.timedelta(days=130), date_created=timezone.now(), status=2)
        cls.res2 = res2
        res3 = Reservation.objects.create(reservation_number='CCCC', student=student2, bed=bed3, date_from=today + timezone.timedelta(days=131),
                                          date_until=today + timezone.timedelta(days=230), date_created=timezone.now(), status=2)
        cls.res3 = res3
        cls.student2 = student2

        comm = Comment.objects.create(
            score=3, review='MALISIMO', date_created=today, status=Bed.ACTIVE, reservation_id=res1.id)
        cls.comm = comm

        cls.student_client = APIClient()
        cls.student_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student).access_token}')

        cls.student_client2 = APIClient()
        cls.student_client2.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student2).access_token}')

        cls.manager_client = APIClient()
        cls.manager_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_manager).access_token}')

    # Test that the status of the reservation changes after being confirmed
    def test_confirm_reservation_manager(self):
        url = reverse('reservation-confirm-reservation')
        id = Reservation.objects.get(reservation_number='BBBB').id
        data = {'id': id}
        response = self.manager_client.put(url, data, format='json')
        stat = Reservation.objects.get(reservation_number='BBBB').status
        self.assertEqual(stat, 3)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test that a 400 error is thrown when trying to confirm a reservation previously confirmed
    def test_failure_confirm_reservation_already_confirmed(self):
        url = reverse('reservation-confirm-reservation')
        id = Reservation.objects.get(reservation_number='AAAA').id
        data = {'id': id}
        response = self.manager_client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Test the status of the reservation and the reject reason is stored after a manager rejects a reservation
    def test_reject_reservation_manager(self):
        url = reverse('reservation-reject-reservation')
        id = Reservation.objects.get(reservation_number='CCCC').id
        data = {'id': id, 'reject_reason': 'No pago'}
        response = self.manager_client.put(url, data, format='json')
        res = Reservation.objects.get(reservation_number='CCCC')
        stat = res.status
        motiv = res.reject_reason
        new_res = Reservation.objects.create(reservation_number='DDDD', student=self.student, bed=self.bed3, date_from=self.today + timezone.timedelta(days=131),
                                             date_until=self.today + timezone.timedelta(days=230), date_created=timezone.now(), status=2)

        self.assertEqual(stat, 1)
        self.assertEqual(motiv, 'No pago')
        self.assertEqual(new_res.status, 2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Creating a reservation a manager and receiving a 201
    def test_create_reservation_manager(self):
        today_date = (self.today + timezone.timedelta(days=230)
                      ).date().isoformat()
        until_date = (self.today + timezone.timedelta(days=330)
                      ).date().isoformat()
        data = {'bed': self.res.bed.id, 'date_from': today_date,
                'date_until': until_date, 'student': self.student.id}
        url = reverse('reservation-list')
        response = self.manager_client.post(url, data, format="json")
        res = Reservation.objects.get(
            bed=self.res.bed.id, date_from=today_date)
        self.assertIsNotNone(res)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Check te active reservation when logged in as a student
    def test_active_reservation(self):
        url = reverse('reservation-active-reservation')
        response = self.student_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual('Resi1', response.data[0]['residence_name'])

    # Check the active reservation when no active reservation
    def test_active_reservation_empty(self):
        url = reverse('reservation-active-reservation')
        response = self.student_client2.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, len(response.data))

    # Check that the document is present in a student
    def test_is_document_present(self):
        final_response = views.is_document_present(self.student.id)
        self.assertEqual(final_response, True)

    # Check that the document is not present in a student
    def test_is_document_present(self):
        final_response = views.is_document_present(self.student3.id)
        self.assertEqual(final_response, False)


class PunctuateResidenceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
        user_student2 = User.objects.create_user(
            username='Dos estudiante', email='dosestudiante@gmail.com', password='Dosestudiante321')
        Group.objects.get_or_create(id=1, name='Student')
        my_group = Group.objects.get(id=1)
        my_group.user_set.add(user_student)
        my_group.user_set.add(user_student2)
        user_manager = User.objects.create_user(
            username='Un gestor', email='ungestor@gmail.com', password='Ungestor321')
        cls.user_manager = user_manager
        Group.objects.get_or_create(id=2, name='Manager')
        my_group = Group.objects.get(id=2)
        my_group.user_set.add(user_manager)

        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.175840915813 -34.89271547922357)'), zone_id=1)
        type1 = ResidenceType.objects.get(pk=1)
        residence1 = Residence.objects.create(name='Resi1', bussines_name='Una resi', rut='2121',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type1)
        room1 = Room.objects.create(name="aroom", residence=residence1)
        bed1 = Bed.objects.create(name='bed1', room=room1)
        bed2 = Bed.objects.create(name='bed2', room=room1)
        bed3 = Bed.objects.create(name='bed3', room=room1)
        cls.bed3 = bed3
        BedPrice.objects.create(price=8500, date_from='2020-11-12', bed=bed1)
        BedPrice.objects.create(price=9500, date_from='2020-11-22', bed=bed2)
        BedPrice.objects.create(price=10500, date_from='2020-11-02', bed=bed3)
        sex = Sex.objects.get(pk=1)
        pay_met = PaymentMethod.objects.get(pk=1)
        cls.pay_met = pay_met
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        cls.student = student1
        student2 = Student.objects.create(
            document='1111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        Student.objects.create(
            document='33333333', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)

        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from=today,
                                          date_until=today + timezone.timedelta(days=30), date_created=today, status=3)
        cls.res = res1
        res2 = Reservation.objects.create(reservation_number='BBBB', student=student1, bed=bed2, date_from=today + timezone.timedelta(days=32),
                                          date_until=today + timezone.timedelta(days=130), date_created=today, status=2)
        cls.res2 = res2
        res3 = Reservation.objects.create(reservation_number='CCCC', student=student2, bed=bed3, date_from=today,
                                          date_until=today + timezone.timedelta(days=230), date_created=today, status=3)
        cls.res3 = res3
        cls.student2 = student2

        comm = Comment.objects.create(
            score=3.0, review='MALISIMO', date_created=today, status=3, reservation_id=res1.id)
        cls.comm = comm
        res4 = Reservation.objects.create(reservation_number='EEEEEE', student=cls.student, bed=cls.bed3, date_from=cls.today - timezone.timedelta(days=131),
                                          date_until=cls.today + timezone.timedelta(days=30), date_created=cls.today)
        cls.res4 = res4
        comm2 = Comment.objects.create(
            score=1.5, review='MALISIMO', date_created=cls.today, reservation_id=res4.id)
        cls.comm2 = comm2

        cls.student_client = APIClient()
        cls.student_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student).access_token}')
        cls.student_client2 = APIClient()
        cls.student_client2.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student2).access_token}')
        cls.manager_client = APIClient()
        cls.manager_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_manager).access_token}')

    # Test if the reservation has a rate associated
    def test_check_rated(self):
        final_response = views.check_rated(self.res)
        self.assertEqual(1, final_response)

    # Throw a 400 error when trying to comment a reservation already commented
    def test_more_than_one_comment_not_allowed(self):
        url = reverse('comment-list')
        data = {'score': 3.0, "review": 'Está bien',
                "reservation_id": self.res.id}
        response = self.student_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Throw a 404 error when trying to comment a reservation with no active association for the student
    def test_no_active_association_error_received(self):
        url = reverse('comment-list')
        data = {'score': 3.0, "review": 'Está bien',
                "reservation_id": self.res2.id}
        response = self.student_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {
                         'detail': "Student doesn't have an existing or active association."})

    # Test that a comment is created and associated to the reservation with the correct status
    def test_comment_created(self):
        res3 = Reservation.objects.create(reservation_number='HHHHHHH', student=self.student, bed=self.bed3, date_from=self.today + timezone.timedelta(days=131),
                                          date_until=self.today + timezone.timedelta(days=230), date_created=self.today, status=3)
        url = reverse('comment-list')
        data = {'score': 3.0, "review": 'Está bien',
                "reservation_id": res3.id}
        response = self.student_client.post(url, data, format='json')
        com = Comment.objects.get(reservation_id=res3.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(com.status, 2)
        self.assertEqual(com.score, 3.0)
        self.assertEqual(com.review, 'Está bien')
        self.assertEqual(response.json(), {
                         'score': '3.0', 'review': 'Está bien', 'reservation': res3.id})

    # Check an authorized error is thrown when a student wants to confirm a comment
    def test_unauthorized_case_comment_approved_by_student(self):
        res3 = Reservation.objects.create(reservation_number='HHHHHHH', student=self.student, bed=self.bed3, date_from=self.today - timezone.timedelta(days=131),
                                          date_until=self.today + timezone.timedelta(days=30), date_created=self.today)
        id = res3.id
        Comment.objects.create(
            score=5.0, review='Genial', date_created=self.today, reservation_id=res3.id)
        url = reverse('comment-confirm-comment', args=[self.comm2.id])
        request = self.student_client.put(url, format='json')
        com2 = Comment.objects.get(reservation_id=id)
        self.assertEqual(2, com2.status)
        self.assertEqual(request.status_code, status.HTTP_401_UNAUTHORIZED)

    # Test that the status of a comment confirmed by a manager is the correspondant to Active
    def test_comment_approved_by_manager(self):
        url = reverse('comment-confirm-comment', args=[self.comm2.id])
        request = self.manager_client.put(url, format='json')
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        com = Comment.objects.get(reservation_id=self.res4.id).status
        self.assertEqual(Bed.ACTIVE, com)

    # Test that the status of a comment rejected by a manager is the correspondant to Cancelled and the reject reason is stored
    def test_comment_rejected_by_manager(self):
        data = {'reject_reason': 'distorsiona la residencia'}
        url = reverse('comment-reject-comment', args=[self.comm2.id])
        request = self.manager_client.put(url, data, format='json')
        com = Comment.objects.get(reservation_id=self.res4.id)
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        self.assertEqual(Bed.CANCELLED, com.status)
        self.assertEqual('distorsiona la residencia', com.reject_reason)


class EmailTestCase(TestCase):
    def test_send_email(self):
        views.send_mail('Notificación', 'Here is the message.',
                        'hola.residenza@gmail.com', [
                            'leticialado@gmail.com'],
                        fail_silently=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Notificación')


class PaymentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.now()
        cls.today = today
        user_student = User.objects.create_user(
            username='Un estudiante', email='unestudiante@gmail.com', password='Unestudiante321')
        Group.objects.get_or_create(id=1, name='Student')
        my_group = Group.objects.get(id=1)
        my_group.user_set.add(user_student)
        user_student2 = User.objects.create_user(
            username='Dos estudiante', email='dosestudiante@gmail.com', password='Unestudiante321')
        my_group.user_set.add(user_student2)
        user_manager = User.objects.create_user(
            username='Un gestor', email='ungestor@gmail.com', password='Ungestor321')
        user_manager2 = User.objects.create_user(
            username='Segundo gestor', email='dosgestor@gmail.com', password='Dosgestor321')
        cls.user_manager = user_manager
        cls.user_manager2 = user_manager2
        Group.objects.get_or_create(id=2, name='Manager')
        my_group = Group.objects.get(id=2)
        my_group.user_set.add(user_manager)
        address = Address.objects.create(pk=101, street='Miguelete', number=1919, apartment=None, location=GEOSGeometry(
            'POINT (-56.175840915813 -34.89271547922357)'), zone_id=1)
        type1 = ResidenceType.objects.get(pk=1)
        residence1 = Residence.objects.create(name='Resi1', bussines_name='Una resi', rut='2121',
                                              mail='unaresi@gmail.com', address=address, manager=user_manager, type=type1)
        residence2 = Residence.objects.create(name='Resi2', bussines_name='Dos resi', rut='2222',
                                              mail='dosresi@gmail.com', address=address, manager=user_manager2, type=type1)
        room1 = Room.objects.create(name="aroom", residence=residence1)
        room4 = Room.objects.create(name="room 4", residence=residence2)
        bed1 = Bed.objects.create(name='bed1', room=room1)
        bed4 = Bed.objects.create(name='bed4', room=room4)
        BedPrice.objects.create(price=8500, date_from='2020-11-12', bed=bed1)
        BedPrice.objects.create(
            price=10500, date_from='2020-11-12', bed=bed4)
        cls.bed1 = bed1
        sex = Sex.objects.get(pk=1)
        pay_met = PaymentMethod.objects.get(pk=1)
        cls.pay_met = pay_met
        student1 = Student.objects.create(
            document='11111111', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student)
        student2 = Student.objects.create(
            document='22222222', document_type=1, birth_date='2000-11-12', sex=sex, user=user_student2)

        cls.student = student1
        cls.student2 = student2
        res1 = Reservation.objects.create(reservation_number='AAAA', student=student1, bed=bed1, date_from=today,
                                          date_until=today + timezone.timedelta(days=30), date_created=timezone.now(), status=3)
        cls.res = res1
        pay1 = Payment.objects.create(
            amount=8500, year_month=202110, payment_date="2021-10-03", payment_method_id=1, reservation_id=res1.id)
        cls.pay1 = pay1
        res4 = Reservation.objects.create(reservation_number='GGGG', student=student2, bed=bed4, date_from=today,
                                          date_until=today + timezone.timedelta(days=30), date_created=timezone.now(), status=3)
        cls.res4 = res4
        pay4 = Payment.objects.create(
            amount=10000, year_month=202110, payment_date="2021-10-03", payment_method_id=1, reservation_id=res4.id)
        pay5 = Payment.objects.create(
            amount=12000, year_month=202111, payment_date="2021-11-06", payment_method_id=1, reservation_id=res4.id)
        cls.pay4 = pay4
        cls.pay5 = pay5

        cls.student_client = APIClient()
        cls.student_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student).access_token}')

        cls.student_client2 = APIClient()
        cls.student_client2.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_student2).access_token}')
        cls.manager_client = APIClient()
        cls.manager_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user_manager).access_token}')

    # Test that a payment is created when manager is logged in
    def test_create_payment_status_when_manager(self):
        url = reverse("payment-list")
        data = {"reservation_number": "AAAA", "amount": 10000, "year_month": 202109,
                "payment_date": "2021-10-12", "payment_method_id": 1}
        response = self.manager_client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Bed.ACTIVE)

    # Test that a payment is created when a student is logged in
    def test_create_payment_status_when_student(self):
        url = reverse("payment-list")
        data = {"amount": 10000, "year_month": 202111,
                "payment_date": "2021-10-12", "payment_method_id": 1}
        response = self.student_client.post(url, data)
        id = response.data[0]['id']
        payment = Payment.objects.get(pk=id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(payment.status, Bed.PENDING)

    #Test that the list of payments is obtained
    def test_obtain_payment_list(self):
        url = reverse("payment-list")
        response = self.student_client2.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    # Test that a payment is confirmed and it's status changed after being confirmed by a manager
    def test_confirm_payment_manager(self):
        id = Payment.objects.filter(
            status=Bed.PENDING, reservation__bed__room__residence__manager=self.user_manager).first().id
        data = {'id': id}
        url = reverse('payment-confirm-payment')
        response = self.manager_client.put(url, data, format='json')
        stat = Payment.objects.get(pk=id).status
        self.assertEqual(stat, Bed.ACTIVE)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test that a payment is rejected and it's status changed after being rejected by a manager
    def test_reject_payment_manager(self):
        id = Payment.objects.filter(
            status=Bed.PENDING, reservation__bed__room__residence__manager=self.user_manager).first().id
        data = {'id': id, 'reject_reason': 'Nunca paga las cuotas'}
        url = reverse('payment-reject-payment')
        response = self.manager_client.put(url, data, format='json')
        payment = Payment.objects.get(pk=id)
        stat = payment.status
        reject = payment.reject_reason
        self.assertEqual(stat, Bed.CANCELLED)
        self.assertEqual(reject, 'Nunca paga las cuotas')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test that an unauthorized error is thrown when a manager tries to reject a payment not from her/his residence
    def test_reject_payment_unauthorized(self):
        id = Payment.objects.filter(
            status=Bed.PENDING, reservation__bed__room__residence__manager=self.user_manager2).first().id
        data = {'id': id, 'reject_reason': 'Nunca paga las cuotas'}
        url = reverse('payment-reject-payment')
        response = self.manager_client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # Test that determine_payments calculate ok the number of iterations to be done when a student pays more than the bed price for a month
    def test_determine_payments(self):
        amount_desired = 12430
        year_month = 202111
        payment_date = "2021-09-12"
        final_response = views.determine_payments(
            amount_desired=amount_desired, year_month=year_month, payment_method=1,
            payment_date=payment_date, res=self.res, observations=None, file=None)
        response = len(final_response.data)
        self.assertEqual(response, 2)

    # Test that determine payments calculate ok the extra when a student pays more than the bed price for a month
    def test_determine_payments_amount(self):
        amount_desired = 12430
        year_month = 202111
        payment_date = "2021-09-12"
        final_response = views.determine_payments(
            amount_desired=amount_desired, year_month=year_month, payment_method=1,
            payment_date=payment_date, res=self.res, observations=None, file=None)
        response = final_response.data[1]['amount']
        self.assertEqual(float(response), 3930)
