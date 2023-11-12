from student.models.student import Student
from residence.models.residence import PaymentMethod, Bed
from residence.models.serviceoffered import ServiceOffered
from user.models import Notification
from common.views import NoActiveAssociation, InactiveElement, NotAuthorized, ObjectDoesntExistOrNotAuthorized, check_permision, obtain_days, obtain_month_year, check_student_exists
from reservation.models.reservation import Reservation, Comment, ServiceConsumed, InvalidRange
from reservation.models.payment import Payment
from reservation.serializers import ReservationSerializer, PaymentSerializer, PaymentCreateStudentSerializer, PaymentListSerializer, CommentListSerializer, CommentCreateSerializer, ServiceConsumedSerializer, ServiceOfferedSerializer, ReservationUploadContractSerializer, PaymentUpdateReceiptSerializer, ServiceConsumedCreateSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, F
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from collections import defaultdict
from datetime import date
import datetime
import uuid
import math

User = get_user_model()


def check_previous_association(student, reservation_id):
    one_res = Reservation.objects.get(pk=reservation_id)
    filter_params = dict(date_from__lte=one_res.date_until,
                         date_until__gte=one_res.date_from)
    try:
        resulta = Reservation.objects.filter(
            student_id=student, status__range=(Bed.PENDING, Bed.ACTIVE), **filter_params).exclude(pk=reservation_id).count()
        return resulta
    except AssociationExists:
        return Response(data={"detail": "There is a previous association for this student."},
                        status=status.HTTP_400_BAD_REQUEST)


def determine_payments(amount_desired, year_month, payment_method, observations, file, payment_date, res):
    pay_met = PaymentMethod.objects.filter(id=payment_method).first()
    a_bed = res.bed
    month, year = obtain_month_year(year_month)
    dayss = obtain_days(month, year)
    date_for_price = datetime.datetime(
        year=year, month=month, day=dayss).date()
    bed_ext_price = a_bed.specific_price(date_for_price)

    if bed_ext_price is not None:
        bed_price = float(bed_ext_price)
        if bed_price < amount_desired:
            repeat = math.ceil(amount_desired / bed_price)
            actual_amount = amount_desired
            payment_list = []
            with transaction.atomic():
                for i in range(1, repeat + 1):
                    if i < repeat:
                        amount = bed_price
                        new_payment = Payment.objects.create(reservation=res, amount=amount, year_month=year_month,
                                                             payment_date=payment_date, observations=observations, payment_method=pay_met, file=file)
                        payment_list.append(new_payment)
                        actual_amount = actual_amount - bed_price
                    elif i == repeat:
                        new_payment_2 = Payment.objects.create(reservation=res, amount=actual_amount, year_month=year_month,
                                                               payment_date=payment_date, observations=observations, payment_method=pay_met, file=file)
                        payment_list.append(new_payment_2)
                    if year_month % 100 == 12:
                        year_month = year_month + 89
                    else:
                        year_month = year_month + 1
                subject = 'Pago creado'
                msge = 'Se ha ingresado un nuevo PAGO del estudiante {0}, número de reserva {1} para el período {2}'.format(
                    payment_list[1].reservation.student, payment_list[1].reservation.reservation_number, payment_list[1].year_month)
                create_notification(subject, msge, Notification.PAYMENT,
                                    payment_list[1].reservation.bed.room.residence.manager, payment_list[1].id)
                serializer = PaymentCreateStudentSerializer(
                    payment_list, many=True)
        else:
            new_payment = Payment.objects.create(
                reservation=res, amount=amount_desired, year_month=year_month, payment_method=pay_met, payment_date=payment_date)
            subject = 'Pago creado'
            msge = 'Se ha ingresado un nuevo PAGO del estudiante {0}, número de reserva {1} para el período {2}'.format(
                new_payment.reservation.student, new_payment.reservation.reservation_number, new_payment.year_month)
            create_notification(subject, msge, Notification.PAYMENT,
                                new_payment.reservation.bed.room.residence.manager, new_payment.id)
            serializer = PaymentCreateStudentSerializer(new_payment)
    return serializer


def obtain_reservation_data(reservations):
    response = []
    for reservation in reservations:
        comment = check_rated(reservation.id)
        data = {
            "reservation_id": reservation.id,
            "reservation_number": reservation.reservation_number,
            "status": reservation.status,
            "rated": True if comment > 0 else False,
            "date_from": reservation.date_from,
            "date_until": reservation.date_until,
            "residence": {
                "id": reservation.bed.room.residence.id,
                "name": reservation.bed.room.residence.name,
                "bed": {
                    "id": reservation.bed.id,
                    "name": reservation.bed.name,
                    "price": reservation.bed.specific_price(reservation.date_from) if reservation.bed else None,
                }
            },
        }
        response.append(data)
    return response


def check_rated(res_id):
    return Comment.objects.filter(reservation_id=res_id).count()


def is_document_present(id):
    document = Student.objects.get(id=id).document
    if document is None or (document.strip()) == '':
        return False
    else:
        return True


def create_reservation_number():
    reservation_number = uuid.uuid4().hex[:10].upper()
    is_in = Reservation.objects.filter(
        reservation_number=reservation_number).exists()
    while is_in:
        reservation_number = uuid.uuid4().hex[:10].upper()
        is_in = Reservation.objects.filter(
            reservation_number=reservation_number).exists()
    return reservation_number


def check_date_from(date_to_be_from):
    today_date = date.today()
    date_from2 = date.fromisoformat(date_to_be_from)
    if (date_from2 < today_date):
        raise InvalidDate('The date selected is invalid')
    return date_to_be_from


def confirm_case(user, one_object, msge, to, subject, type_not):
    perm = check_permision(user)
    try:
        if perm == 1:
            try:
                previous_status = one_object.status
                if previous_status == Bed.ACTIVE:
                    raise AlreadyAccepted(
                        "The object has already been approved.")
                elif previous_status == Bed.INACTIVE:
                    raise InactiveElement("The object is inactive.")
                with transaction.atomic():
                    one_object.status = Bed.ACTIVE
                    one_object.save()
                    create_notification(
                        subject, msge, type_not, to, one_object.id)
                    send_mail(subject, msge,
                              settings.EMAIL_HOST_USER, [to.email])
                return Response()
            except AssociationExists:
                return Response(data={"detail": "There is a previous association for this student."},
                                status=status.HTTP_400_BAD_REQUEST)
            except AlreadyAccepted:
                return Response(data={"detail": "This transaction has already been accepted."},
                                status=status.HTTP_400_BAD_REQUEST)
            except InactiveElement:
                return Response(data={"detail": "This transaction is inactive."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            raise NotAuthorized("user not authorized")
    except NotAuthorized:
        return Response(data={"detail": "The user is not authorized to do this."},
                        status=status.HTTP_401_UNAUTHORIZED)


def reject_case(user, reject_reason, one_object, msge, to, subject, type_not):
    perm = check_permision(user)
    try:
        previous_status = one_object.status
        if previous_status == Bed.CANCELLED:
            raise AlreadyCancelled(
                "The object has already been cancelled.")
        elif previous_status == Bed.INACTIVE:
            raise InactiveElement("The object is inactive.")
        else:
            if perm == 1:
                rejec_reason = reject_reason
                if rejec_reason is None:
                    raise NotNullField(
                        "Theres is a not allowed blank field")
            else:
                rejec_reason = 'Cancelled by user'
            one_object.status = Bed.CANCELLED
            one_object.reject_reason = rejec_reason
            one_object.date_cancelled = timezone.now()
            subject = "Aviso de CANCELACIÓN"
            with transaction.atomic():
                create_notification(subject, msge, type_not, to, one_object.id)
                send_mail(subject, msge, settings.EMAIL_HOST_USER, [
                    to.email])
                one_object.save()
            return Response()
    except NotNullField:
        return Response(data={"detail": "Rejec reason field could not be empty."}, status=status.HTTP_400_BAD_REQUEST)
    except AlreadyCancelled:
        return Response(data={"detail": "This transaction has already been cancelled."}, status=status.HTTP_400_BAD_REQUEST)


def create_notification(title, description, type_not, user, id):
    today = timezone.now()
    base_URL = 'sistemaresidenza'
    link = '{0}/{1}/{2}'.format(base_URL,
                                Notification.notification_status_dict[type_not].lower(), id)
    return Notification.objects.create(
        title=title, description=description, type=type_not, user=user, date_created=today, link=link)


class ReservationUploadContractViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Reservation.objects.all()
    serializer_class = ReservationUploadContractSerializer

    def update(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                instance = self.get_object()
                if instance.bed.room.residence.manager == request.user:
                    instance.contract = request.data.get('contract')
                    instance.save()
                    serializer = ReservationUploadContractSerializer(
                        data=instance)
                    serializer.is_valid()
                    return Response(data=serializer.data)
                else:
                    raise ObjectDoesntExistOrNotAuthorized()
            else:
                raise ObjectDoesntExistOrNotAuthorized()

        except ObjectDoesntExistOrNotAuthorized:
            return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)


def obtain_student(student, user_id, perm):
    try:
        if perm == 1:
            id = student
        elif perm == 0:
            student = check_student_exists(user_id)
            if student is not None:
                id = student.id
            else:
                id = None
        else:
            raise ObjectDoesntExistOrNotAuthorized("The student doesn't exist")
        return id
    except ObjectDoesntExistOrNotAuthorized:
        return Response(data={"detail": "The date selected is invalid"},
                        status=status.HTTP_400_BAD_REQUEST)


class ReservationViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

    def create(self, request, *args, **kwargs):
        today = timezone.now()
        perm = check_permision(request.user)
        user_id = request.user.id
        student = request.data.get('student')
        id = obtain_student(student, user_id, perm)
        try:
            if id is not None:
                is_document = is_document_present(id)
                try:
                    if is_document:
                        reservation_number = create_reservation_number()
                        title = 'Reserva creada'
                        type_not = Notification.RESERVATION
                        date_until = request.data.get('date_until')
                        date_from = request.data.get('date_from')
                        bed_id = request.data.get('bed')
                        filter_params = dict(date_from__lte=date_until,
                                             date_until__gte=date_from)
                        if perm == 1:
                            bed_query = Bed.objects.filter(
                                pk=bed_id, room__residence__manager=request.user)
                            if bed_query.count() > 0:
                                bed = bed_query.first()
                            else:
                                raise ObjectDoesntExistOrNotAuthorized()
                            student_id = request.data.get('student')
                            student = Student.objects.get(pk=student_id)
                            resulta = Reservation.objects.filter(status__range=(Bed.PENDING, Bed.ACTIVE),
                                                                 student_id=student, **filter_params).count()
                            if resulta == 0:
                                user = User.objects.filter(
                                    student=student).first()
                                obj = Reservation.objects.create(
                                    reservation_number=reservation_number, date_from=date_from, date_until=date_until, status=Bed.ACTIVE, date_created=today, bed=bed, student=student)
                                description = 'Se ha creado una nueva RESERVA para la Residencia {0}'.format(
                                    obj.bed.room.residence)
                                create_notification(
                                    title, description, type_not, user, obj.id)
                                serializer = ReservationSerializer(data=obj)
                                serializer.is_valid()
                                return Response(data=serializer.data, status=status.HTTP_201_CREATED)
                            else:
                                raise AssociationExists(
                                    "Previous association exists")
                        elif perm == 0:
                            bed = Bed.objects.get(pk=bed_id)
                            student_id = id
                            student = Student.objects.get(pk=student_id)
                            try:
                                date_to_be_from = request.data.get('date_from')
                                date_from = check_date_from(date_to_be_from)
                            except InvalidDate:
                                return Response(data={"detail": "The date selected is invalid"},
                                                status=status.HTTP_400_BAD_REQUEST)
                            resulta = Reservation.objects.filter(
                                student=student, status__range=(Bed.PENDING, Bed.ACTIVE), **filter_params).count()
                            if resulta == 0:
                                user = User.objects.filter(
                                    pk=bed.room.residence.manager.id).first()
                                with transaction.atomic():
                                    obj = Reservation.objects.create(
                                        reservation_number=reservation_number, date_from=date_from, date_until=date_until, date_created=today, bed=bed, student=student)
                                    description = 'Se ha creado una nueva RESERVA para la cama {0} , estudiante {1} con el número de reserva {2}'.format(
                                        obj.bed, obj.student, obj.reservation_number)
                                    create_notification(
                                        title, description, type_not, user, obj.id)
                                    serializer = ReservationSerializer(
                                        data=obj)
                                    serializer.is_valid()
                                    return Response(data=serializer.data, status=status.HTTP_201_CREATED)
                            else:
                                raise AssociationExists(
                                    "Previous association exists")
                    else:
                        raise DocumentNeeded(
                            "The student document is needed for this operation.")
                except AssociationExists:
                    return Response(data={"detail": "There is a previous association for this student."},
                                    status=status.HTTP_400_BAD_REQUEST)
                except DocumentNeeded:
                    return Response(data={"detail": "The student document is needed for this operation."},
                                    status=status.HTTP_400_BAD_REQUEST)
                except ObjectDoesntExistOrNotAuthorized:
                    return Response(data={"detail": "The bed does not exist on DataBase or you are not authorized to access."},
                                    status=status.HTTP_401_UNAUTHORIZED)
            else:
                raise IncompleteInformation()
        except IncompleteInformation:
            return Response(data={"detail": "It is necessary to complete personal information to achieve this operation."},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        instance = self.get_object()
        try:
            perm = check_permision(request.user)
            if perm == 1:
                date_until = request.data.get('date_until')
                student_id = request.data.get('student')
                student = Student.objects.get(pk=student_id)
                status = request.data.get('status')
                instance.date_until = date_until
                instance.student = student
                instance.status = status
                instance.save()
                return Response()
            else:
                raise NotAuthorized()
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    def list(self, request):
        reservations = ''
        perm = check_permision(request.user)
        today = timezone.now()
        if perm == 1:
            residence = request.GET.get('residence')
            reservations = self.queryset.prefetch_related(
                'bed__room', 'student__user').filter(bed__room__residence__manager=request.user, bed__room__residence=residence).order_by('-status')
            statuss = defaultdict(dict)
            for one_sat in Bed.STATUS:
                statuss[one_sat[1]] = [

                    {
                        "reservation_id": reservation.id,
                        "reservation_number": reservation.reservation_number,
                        "date_created": reservation.date_created,
                        "date_from": reservation.date_from,
                        "date_until": reservation.date_until,
                        "contract": reservation.contract.url if reservation.contract else None,
                        "room": {
                            "id": reservation.bed.room.id,
                            "name": reservation.bed.room.name,
                        },
                        "bed": {
                            "id": reservation.bed.id,
                            "name": reservation.bed.name,
                            "price": reservation.bed.specific_price(reservation.date_until) if reservation.bed.specific_price(reservation.date_until) else None,
                        },
                        "student": {
                            "id": reservation.student.id,
                            "first_name": reservation.student.user.first_name,
                            "last_name": reservation.student.user.last_name,
                        }

                    } for reservation in reservations if reservation.status == one_sat[0]]
            data = statuss

        elif perm == 0:
            reservations = self.queryset.prefetch_related(
                'bed__room', 'student__user').filter((Q(bed__bedprice__date_until__gte=today) | Q(bed__bedprice__date_until__isnull=True)), student__user=request.user).order_by('-status', '-date_from')
            data = obtain_reservation_data(reservations)
        return Response(data)

    @classmethod
    def active_reservation_method(cls, user):
        today = timezone.now()
        reservations = cls.queryset.prefetch_related(
            'bed__room', 'student__user').filter((Q(bed__bedprice__date_until__gte=today) | Q(bed__bedprice__date_until__isnull=True)), date_until__gte=today, date_from__lte=today, status=Bed.ACTIVE,  student__user=user)
        comment = 0
        if reservations.count() > 0:
            res_id = reservations.first().id
            comment = check_rated(res_id)
        data = [
            {
                "reservation_id": reservation.id,
                "reservation_number": reservation.reservation_number,
                "status": reservation.status,
                "date_until": reservation.date_until,
                "residence_name": reservation.bed.room.residence.name,
                "rated": True if comment > 0 else False,

            } for reservation in reservations]
        return data

    @action(detail=False, methods=['GET'], url_path='active-reservation')
    def active_reservation(self, request):
        user = request.user
        data = self.active_reservation_method(user)
        return Response(data)

    @action(detail=False, methods=['GET'], url_path='pending-approve')
    def pending_approve(self, request):
        today = timezone.now()
        perm = check_permision(request.user)
        try:
            if perm == 1:
                reservations = self.queryset.prefetch_related(
                    'bed__room', 'student__user').filter((Q(bed__bedprice__date_until__gte=today) | Q(bed__bedprice__date_until__isnull=True)), status=Bed.PENDING,  bed__room__residence__manager=request.user)
                data = [
                    {
                        "reservation_id": reservation.id,
                        "status": reservation.status,
                        "student": {
                            "id": reservation.student.id,
                            "first_name": reservation.student.user.first_name,
                            "last_name": reservation.student.user.last_name,
                        },
                        "room": {
                            "id": reservation.bed.room.id,
                            "name": reservation.bed.room.name,
                            "bed": {
                                "id": reservation.bed.id,
                                "name": reservation.bed.name,
                                "price": reservation.bed.specific_price(reservation.date_until) if reservation.bed.specific_price(reservation.date_until) else None,
                            }
                        },
                        "dates": {
                            "date_created": reservation.date_created,
                            "date_from": reservation.date_from,
                            "date_until": reservation.date_until,
                        }

                    } for reservation in reservations]
                return Response(data)
            else:
                raise NotAuthorized("User not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['PUT'], url_path='pending-approve/confirm-reservation')
    def confirm_reservation(self, request):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                reservation_id = request.data.get('id')
                try:
                    one_reservation = Reservation.objects.filter(
                        pk=reservation_id, bed__room__residence__manager=request.user)
                    if one_reservation.count() != 0:
                        one_reservation = one_reservation.first()
                        student = one_reservation.student_id
                        resulta = check_previous_association(
                            student, reservation_id)
                        try:
                            if resulta == 0:
                                msge = f"Su reserva para la residencia {one_reservation.bed.room.residence.name} ha sido confirmada"
                                to = one_reservation.student.user
                                subject = "Aviso de CONFIRMACIÓN"
                                user = request.user
                                return confirm_case(user, one_reservation, msge, to, subject, Notification.RESERVATION)
                            else:
                                raise AssociationExists(
                                    "There is a previous association for this student.")
                        except AssociationExists:
                            return Response(data={"detail": "There is another association for this dates."},
                                            status=status.HTTP_400_BAD_REQUEST)
                    else:
                        raise ObjectDoesntExistOrNotAuthorized(
                            "The association does not exist or you are not authorized to access.")
                except ObjectDoesntExistOrNotAuthorized:
                    return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                                    status=status.HTTP_400_BAD_REQUEST)
                except Reservation.DoesNotExist:
                    return Response(data={"detail": "Object doesn't exist in DataBase."},
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['PUT'], url_path='pending-approve/reject-reservation')
    def reject_reservation(self, request):
        perm = check_permision(request.user)
        if perm == 1:
            reservation_id = request.data.get('id')
            try:
                one_reservation = Reservation.objects.filter(
                    pk=reservation_id, bed__room__residence__manager=request.user)
                if one_reservation.count() != 0:
                    one_reservation = one_reservation.first()
                    if one_reservation.reject_reason is None:
                        reject_reason = "Ninguno"
                    else:
                        reject_reason = one_reservation.reject_reason
                    msge = f"Su RESERVA para la residencia {one_reservation.bed.room.residence.name} ha sido CANCELADA. Comentarios realizados:  {reject_reason}"
                    to = one_reservation.student.user
                    user = request.user
                    reject_reason = request.data.get('reject_reason')
                    subject = "Aviso de CANCELACIÓN"
                    return reject_case(user, reject_reason, one_reservation, msge, to, subject, Notification.RESERVATION)
                else:
                    raise ObjectDoesntExistOrNotAuthorized(
                        "The association does not exist or you are not authorized to access.")
            except ObjectDoesntExistOrNotAuthorized:
                return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                                status=status.HTTP_400_BAD_REQUEST)
            except Reservation.DoesNotExist:
                return Response(data={"detail": "Object doesn't exist in DataBase."},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            reservation_id = request.data.get('id')
            try:
                one_reservation = Reservation.objects.filter(
                    pk=reservation_id, student__user=request.user, status=2)
                if one_reservation.count() != 0:
                    one_reservation = one_reservation.first()
                    if one_reservation.reject_reason is None:
                        reject_reason = "Ninguno"
                    else:
                        reject_reason = one_reservation.reject_reason
                    msge = f"Su RESERVA para la residencia {one_reservation.bed.room.residence.name} ha sido CANCELADA. Comentarios realizados:  {reject_reason}"
                    to = one_reservation.student.user
                    user = request.user
                    reject_reason = request.data.get('reject_reason')
                    subject = "Aviso de CANCELACIÓN"
                    return reject_case(user, reject_reason, one_reservation, msge, to, subject, Notification.RESERVATION)
                else:
                    raise ObjectDoesntExistOrNotAuthorized(
                        "The association does not exist or you are not authorized to access.")

            except ObjectDoesntExistOrNotAuthorized:
                return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                                status=status.HTTP_400_BAD_REQUEST)


class PaymentReceiptViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentUpdateReceiptSerializer

    def update(self, request, pk=None):
        perm = check_permision(request.user)
        instance = self.get_object()
        try:
            if perm == 1:
                if instance.reservation.bed.room.residence.manager == request.user:
                    instance.file = request.data.get('file')
                    instance.save()
                    serializer = PaymentUpdateReceiptSerializer(data=instance)
                    serializer.is_valid()
                else:
                    raise ObjectDoesntExistOrNotAuthorized()
            elif perm == 0:
                if instance.reservation.student.user == request.user:
                    instance.file = request.data.get('file')
                    instance.save()
                    serializer = PaymentUpdateReceiptSerializer(data=instance)
                    serializer.is_valid()
                    return Response(data=serializer.data)
                else:
                    raise ObjectDoesntExistOrNotAuthorized()
            else:
                raise NotAuthorized()
        except ObjectDoesntExistOrNotAuthorized:
            return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)
        except NotAuthorized:
            return Response(data={"detail": "You are not authorized to access."},
                            status=status.HTTP_401_UNAUTHORIZED)


class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Payment.objects.all()

    serializers = {
        'create': PaymentCreateStudentSerializer,
        'list': PaymentListSerializer,
        'default': PaymentListSerializer
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action,
                                    self.serializers.get('default'))

    def create(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        today = timezone.now()
        if perm == 1:
            try:
                year_month = request.data.get('year_month')
                reservation_number = request.data.get('reservation_number')
                amount = request.data.get('amount')
                payment_date = request.data.get('payment_date')
                pay_met = request.data.get('payment_method_id')
                payment_method = PaymentMethod.objects.get(pk=pay_met)
                try:
                    if reservation_number is None:
                        raise IncompleteInformation()
                    reservation = Reservation.objects.get(
                        reservation_number=reservation_number, bed__room__residence__manager=request.user)
                except ObjectDoesNotExist:
                    return Response(data={"detail": "The reservation number is not valid or does not exist."},
                                    status=status.HTTP_400_BAD_REQUEST)
                except IncompleteInformation:
                    return Response(data={"detail": "The reservation number is needed."},
                                    status=status.HTTP_400_BAD_REQUEST)

                if reservation.status in (Bed.CANCELLED, Bed.PENDING):
                    raise NoActiveAssociation(
                        "The reservation_number does not exist or you are not authorized to access.")
                month, year = obtain_month_year(year_month)

                if (month >= 1 and month <= 12) and (year >= 1990 and year < 2100):
                    with transaction.atomic():
                        new_payment = Payment.objects.create(
                            reservation=reservation, status=Bed.ACTIVE, amount=amount, year_month=year_month, payment_date=payment_date, payment_method=payment_method)
                        subject = 'Pago creado'
                        msge = 'Se ha ingresado un nuevo PAGO para el período {0} en la Residencia {1}'.format(
                            new_payment.year_month, new_payment.reservation.bed.room.residence)
                        create_notification(
                            subject, msge, Notification.PAYMENT, new_payment.reservation.student.user, new_payment.id)
                        serializer = PaymentSerializer(new_payment)
                        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
                else:
                    raise ValidationError('There is an invalid input')
            except ValidationError:
                return Response(data={"detail": "The year month format is not valid."},
                                status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesntExistOrNotAuthorized:
                return Response(data={"detail": "The year month format is not valid."},
                                status=status.HTTP_400_BAD_REQUEST)
            except NoActiveAssociation:
                return Response(data={"detail": "There is no active or fulfilled reservation for this payment."},
                                status=status.HTTP_400_BAD_REQUEST)
        elif perm == 0:
            try:
                one_reser = Reservation.objects.filter((Q(bed__bedprice__date_until__gte=today) | Q(bed__bedprice__date_until__isnull=True)),
                                                       status=Bed.ACTIVE, date_from__lte=today, date_until__gte=today, student__user=self.request.user)
                if one_reser.count() == 1:
                    res = one_reser.first()
                    amount_desired = float(request.data.get('amount'))
                    year_month = request.data.get('year_month')
                    payment_method = request.data.get('payment_method_id')
                    observations = request.data.get('observations')
                    file = request.data.get('file')
                    payment_date = request.data.get('payment_date')
                    serializer = determine_payments(
                        amount_desired, int(year_month), payment_method, observations, file, payment_date, res)

                    return Response(data=serializer.data, status=status.HTTP_201_CREATED)
                elif one_reser.count() > 1:
                    raise MultipleAssociations()
                else:
                    raise NoActiveAssociation(
                        "The student doesn't have an existing reservation")

            except NoActiveAssociation:
                return Response(data={"detail": "Student doesn't have an existing or active association."},
                                status=status.HTTP_404_NOT_FOUND)
            except MultipleAssociations:
                return Response(data={"detail": "Student has more than one active association."},
                                status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        perm = check_permision(request.user)
        if perm == 1:
            payments = self.queryset.filter(
                reservation__status=Bed.ACTIVE, reservation__bed__room__residence__manager=self.request.user).prefetch_related('payment_method', 'reservation').order_by('reservation__reservation_number')
            statuss = defaultdict(dict)
            for one_sat in Bed.STATUS:
                statuss[one_sat[1]] = [
                    {
                        "reservation_number": payment.reservation.reservation_number,
                        "student": payment.reservation.student.id,
                        "student_first_name": payment.reservation.student.user.first_name,
                        "student_last_name": payment.reservation.student.user.last_name,
                        "payment_id": payment.id,
                        "amount": payment.amount,
                        "year_month": payment.year_month,
                        "payment_date": payment.payment_date,
                        "payment_method": payment.payment_method.description,
                        "payment_file": payment.file.url if payment.file else None,
                        "extension": payment.file.name.split('.')[-1] if payment.file else None,
                        "reject_reason": payment.reject_reason
                    } for payment in payments if payment.status == one_sat[0]]
            data = statuss
            return Response(data, status=status.HTTP_200_OK)
        elif perm == 0:
            payments = self.queryset.filter(reservation__student__user=self.request.user).prefetch_related(
                'reservation__bed__room__residence', 'reservation__student', 'payment_method').order_by('-reservation__status', 'reservation__bed__room__residence')
            data = [
                {
                    "residence": payment.reservation.bed.room.residence.name,
                    "reservation_number": payment.reservation.reservation_number,
                    "amount": payment.amount,
                    "year_month": payment.year_month,
                    "payment_date": payment.payment_date,
                    "payment_method_id": payment.payment_method_id,
                    "payment_method_description": payment.payment_method.description,
                    "observations": payment.observations,
                    "status": payment.status,
                    "reject_reason": payment.reject_reason
                } for payment in payments]
        else:
            raise NotAuthorized()
        return Response(data, status=status.HTTP_200_OK)

    @ action(detail=False, methods=['PUT'], url_path='pending-approve/confirm-payment')
    def confirm_payment(self, request):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                payment_id = request.data.get('id')
                try:
                    one_payment = Payment.objects.filter(
                        id=payment_id, reservation__bed__room__residence__manager=request.user).first()
                    msge = f"Su PAGO para la residencia {one_payment.reservation.bed.room.residence.name} ha sido CONFIRMADO"
                    if one_payment is not None:
                        to = one_payment.reservation.student.user
                        subject = "Aviso de CONFIRMACIÓN"
                        user = request.user
                        return confirm_case(user, one_payment, msge, to, subject, Notification.PAYMENT)
                    else:
                        raise ObjectDoesntExistOrNotAuthorized()
                except Payment.DoesNotExist:
                    return Response(data={"detail": "Object doesn't exist in DataBase."},
                                    status=status.HTTP_404_NOT_FOUND)
                except ObjectDoesntExistOrNotAuthorized:
                    return Response(data={"detail": "Object doesn't exist or you are not authorized to access."},
                                    status=status.HTTP_401_UNAUTHORIZED)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    @ action(detail=False, methods=['PUT'], url_path='pending-approve/reject-payment')
    def reject_payment(self, request):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                payment_id = request.data.get('id')
                try:
                    one_payment = Payment.objects.filter(
                        id=payment_id, reservation__bed__room__residence__manager=request.user).first()
                    if one_payment is not None:
                        if one_payment.reject_reason is None:
                            reject_reason = "Ninguno"
                        else:
                            reject_reason = one_payment.reject_reason
                        msge = f"Su PAGO para la residencia {one_payment.reservation.bed.room.residence.name} ha sido CANCELADO. Comentarios realizados:  {reject_reason}"
                        to = one_payment.reservation.student.user
                        user = request.user
                        reject_reason = request.data.get('reject_reason')
                        subject = "Aviso de CANCELACIÓN"
                        return reject_case(user, reject_reason, one_payment, msge, to, subject, Notification.PAYMENT)
                    else:
                        raise ObjectDoesntExistOrNotAuthorized()
                except Payment.DoesNotExist:
                    return Response(data={"detail": "Object doesn't exist in DataBase."},
                                    status=status.HTTP_404_NOT_FOUND)
                except ObjectDoesntExistOrNotAuthorized:
                    return Response(data={"detail": "Object doesn't exist in DataBase."},
                                    status=status.HTTP_401_UNAUTHORIZED)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = ServiceOffered.objects.all()
    serializer_class = ServiceOfferedSerializer

    def list(self, request):
        if request.GET.get('residence'):
            resid = request.GET.get('residence')
            queryset = ServiceOffered.objects.filter(residence=resid).prefetch_related(
                'servicetype').values('service__id', 'service__description')
            data = [
                {
                    "service_id": service['service__id'],
                    "description": service['service__description']
                } for service in queryset]
            return Response(data)
        else:
            return super().list(self, request)


class ServiceConsumedViewSet(viewsets.ModelViewSet):
    queryset = ServiceConsumed.objects.all()
    serializer_class = ServiceConsumedSerializer

    serializers = {
        'create': ServiceConsumedCreateSerializer,
        'default': ServiceConsumedSerializer
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action,
                                    self.serializers.get('default'))

    def create(self, request, *args, **kwargs):
        reservation = request.data.get('reservation')
        service = request.data.get('service')
        perm = check_permision(request.user)
        try:
            if perm == 1:
                res = Reservation.objects.get(pk=reservation)
                try:
                    if res.bed.room.residence.manager == request.user:
                        is_in = False
                        list_serv = ServiceOffered.objects.filter(
                            residence=res.bed.room.residence).all()
                        for ser_of in list_serv:
                            if ser_of.service_id == service:
                                is_in = True
                        if is_in:
                            id = request.data.get('service')
                            serviceoffered = ServiceOffered.objects.get(pk=id)
                            request.data.update({'service': serviceoffered})
                            request.data.update({'reservation': res})
                            new_service = ServiceConsumed.objects.create(
                                **request.data)

                            subject = 'Servicio creado'
                            msge = 'Se ha ingresado un nuevo SERVICIO para tu reserva en la residencia {0}'.format(
                                new_service.reservation.bed.room.residence)
                            create_notification(subject, msge, Notification.SERVICE,
                                                new_service.reservation.student.user, new_service.id)
                            serializer = ServiceConsumedCreateSerializer(
                                new_service)
                            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
                        else:
                            raise ObjectDoesntExistOrNotAuthorized()
                    else:
                        raise ObjectDoesntExistOrNotAuthorized()
                except ObjectDoesntExistOrNotAuthorized:
                    return Response(data={"detail": "The object does not exist in DB or you are not authorized to access."},
                                    status=status.HTTP_401_UNAUTHORIZED)
            else:
                raise NotAuthorized()
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    def list(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                qs = Reservation.objects.filter((Q(status=Bed.ACTIVE) | Q(status=Bed.INACTIVE)), bed__room__residence__manager=request.user).prefetch_related(
                    'service').annotate(service_desc=F('service__service__description')).distinct('reservation_number')
            elif perm == 0:
                qs = Reservation.objects.filter((Q(status=Bed.ACTIVE) | Q(status=Bed.INACTIVE)), student__user=request.user).prefetch_related(
                    'service').annotate(service_desc=F('service__service__description')).distinct('reservation_number')
            else:
                raise NotAuthorized()
            listofres = []
            for q in qs:
                data = [
                    {
                        "reservation_number": q.reservation_number,
                        "reservation_id": q.id,
                        "student_first_name": q.student.user.first_name,
                        "student_last_name": q.student.user.last_name,
                        "student_document": q.student.document,
                        "services_consumed": ServiceConsumedSerializer(q.serviceconsumed_set.all(), many=True).data}
                ]
                listofres.append(data)
            return Response(listofres, status=status.HTTP_200_OK)
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    def update(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                date_cancelled = request.data.get('date_cancelled')
                payment_date = request.data.get('payment_date')
                instance = self.get_object()
                if instance.reservation.bed.room.residence.manager == request.user:
                    if date_cancelled is not None:
                        instance.date_cancelled = date_cancelled
                    if payment_date is not None:
                        instance.payment_date = payment_date
                    instance.save()
                    serializer = ServiceConsumedSerializer(data=instance)
                    serializer.is_valid()
                    return Response(data=serializer.data)
            else:
                raise NotAuthorized()
        except NotAuthorized:
            return Response(data={"detail": "You are not authorized to access."},
                            status=status.HTTP_401_UNAUTHORIZED)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()

    serializers = {
        'create': CommentCreateSerializer,
        'default': CommentListSerializer
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action,
                                    self.serializers.get('default'))

    def create(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        today = timezone.now()
        try:
            if perm == 0:
                reservation_id = request.data.get('reservation_id')
                queryset = Reservation.objects.prefetch_related(
                    'bed__room', 'student__user').filter((Q(status=Bed.ACTIVE) | Q(status=Bed.INACTIVE)), id=reservation_id, student__user=request.user)
                if queryset.count() > 0:
                    reservation = queryset.first()
                    resulta = Comment.objects.filter(
                        reservation_id=reservation.id).count()
                    if resulta == 0:
                        try:
                            new_comment = Comment.objects.create(
                                reservation=reservation, status=Bed.PENDING, date_created=today, **request.data)
                            subject = 'Comentario creado'
                            msge = 'Se ha realizado un nuevo COMENTARIO del estudiante {0}, número de reserva {1}'.format(
                                new_comment.reservation.student, new_comment.reservation.reservation_number)
                            create_notification(subject, msge, Notification.COMMENT,
                                                new_comment.reservation.bed.room.residence.manager, new_comment.id)
                            serializer = CommentCreateSerializer(new_comment)
                            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
                        except InvalidRange:
                            return Response(data={"detail": "The score range must be between 1 and 5"},
                                            status=status.HTTP_401_UNAUTHORIZED)
                    else:
                        raise AssociationExists("Previous comment exists")

                else:
                    raise NoActiveAssociation(
                        "The student doesn't have an existing reservation")

            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)
        except NoActiveAssociation:
            return Response(data={"detail": "Student doesn't have an existing or active association."},
                            status=status.HTTP_404_NOT_FOUND)
        except AssociationExists:
            return Response(data={"detail": "There is a previous comment for this reservation."},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['PUT'], url_path='confirm-comment')
    def confirm_comment(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                one_comment = Comment.objects.get(pk=pk)
                msge = f"Su COMENTARIO para la residencia {one_comment.reservation.bed.room.residence.name} ha sido CONFIRMADO"
                to = one_comment.reservation.student.user
                subject = "Aviso de CONFIRMACIÓN"
                user = request.user
                return confirm_case(user, one_comment, msge, to, subject, Notification.COMMENT)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=True, methods=['PUT'], url_path='reject-comment')
    def reject_comment(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                today = timezone.now()
                one_comment = Comment.objects.get(pk=pk)
                if one_comment.reject_reason is None:
                    reject_reason = "Ninguno"
                else:
                    reject_reason = one_comment.reject_reason
                msge = f"Su COMENTARIO para la residencia {one_comment.reservation.bed.room.residence.name} ha sido CANCELADO. Comentarios realizados:  {one_comment.reject_reason}"
                to = one_comment.reservation.student.user
                user = request.user
                reject_reason = request.data.get('reject_reason')
                one_comment.date_rejected = today
                subject = "Aviso de CANCELACIÓN"
                return reject_case(user, reject_reason, one_comment, msge, to, subject, Notification.COMMENT)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    def list(self, request):
        residence = request.GET.get('residence')
        perm = check_permision(request.user)
        if perm == 1:
            comments = Comment.objects.filter(
                reservation__bed__room__residence=residence)
            statuss = defaultdict(dict)
            for one_sat in Bed.STATUS:
                statuss[one_sat[1]] = [
                    {
                        "first_name": comment.reservation.student.user.first_name,
                        "last_name": comment.reservation.student.user.last_name,
                        "mail": comment.reservation.student.user.email,
                        "reservation_number": comment.reservation.reservation_number,
                        "user_id": comment.reservation.student.user.id,
                        "comment_id": comment.id,
                        "rate": comment.score,
                        "comment": comment.review,
                        "reject_reason": comment.reject_reason,
                        "date_rejected": comment.date_rejected
                    } for comment in comments if comment.status == one_sat[0]]
            data = statuss
            return Response(data)
        elif perm == -1 or perm == 0:
            comments = Comment.objects.filter(
                reservation__bed__room__residence=residence, status=Bed.ACTIVE)
            data = [
                {
                    "username": comment.reservation.student.user.username,
                    "user_id": comment.reservation.student.user.id,
                    "rate": comment.score,
                    "comment": comment.review,
                } for comment in comments]
            return Response(data)


class AlreadyCancelled(Exception):
    pass


class AlreadyAccepted(Exception):
    pass


class AssociationExists(Exception):
    pass


class DocumentNeeded(Exception):
    pass


class InvalidDate(Exception):
    pass


class NotNullField(Exception):
    pass


class PermissionGroupNotAssigned(Exception):
    pass


class IncompleteInformation(Exception):
    pass


class MultipleAssociations(Exception):
    pass
