from reservation.models.reservation import Reservation
from reservation.serializers import PaymentIdSerializer
from reservation.views import MultipleAssociations, ReservationSerializer
from residence.models.residence import Bed
from student.models.student import Student, Tutor, RELATION_CHOICES
from student.serializers import StudentOrigianSerializer, StudentSerializer, TutorSerializer, TutorCreateSerializer, StudentUpdateImageSerializer
from common.views import ObjectDoesntExistOrNotAuthorized, NotAuthorized, UruguayanDocument, check_permision
from django.contrib.auth import get_user_model
from django.db.models import F, Q, Prefetch
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action

User = get_user_model()


class StudentUpdateImageViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Student.objects.all()
    serializer_clas = StudentUpdateImageSerializer

    def update(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 0:
                instance = self.get_object()
                if instance.user == request.user:
                    instance.image = request.data.get('image')
                    instance.save()
                    serializer = StudentUpdateImageSerializer(data=instance)
                    serializer.is_valid()
                    return Response(data=serializer.data)
                else:
                    raise ObjectDoesntExistOrNotAuthorized()
            else:
                raise ObjectDoesntExistOrNotAuthorized()
        except ObjectDoesntExistOrNotAuthorized:
            return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)


class StudentViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Student.objects.all()

    serializers = {
        'list': StudentSerializer,
        'default': StudentSerializer,
        'create': StudentOrigianSerializer,
        'update': StudentOrigianSerializer
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action,
                                    self.serializers.get('default'))

    def create(self, request, *args, **kwargs):
        try:
            document_type_new = None
            perm = check_permision(request.user)
            if perm == 0:
                document_display_type = request.data.get("document_type")
                for doc_type in Student.DOCUMENT:
                    if doc_type[1] == document_display_type:
                        document_type_new = doc_type[0]
                request.data["user"] = request.user.id
                request.data["document_type"] = document_type_new
                document = request.data.get('document')
                validate_document_proc(
                    self, request, document, document_type_new)
                return super().create(request, *args, **kwargs)
            elif perm == 1:
                request.data.get("user_id")
                return super().create(request)
            else:
                raise NotAuthorized("User not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)
        except DocumentNotValid:
            return Response(data={"detail": "The document provided is not valid."},
                            status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        today = timezone.now()
        try:
            perm = check_permision(request.user)
            if perm == 1:
                queryset = Student.objects.filter(reservation__bed__room__residence__manager=self.request.user, reservation__status=Bed.ACTIVE, reservation__date_until__gte=today).prefetch_related('user', 'sex').annotate(user_first_name=F('user__first_name'), user_last_name=F('user__last_name'), sex_desc=F('sex__description')).distinct('id')
                serializer = StudentSerializer(data=queryset, many=True)
                serializer.is_valid()
                return Response(data=serializer.data)
            else:
                raise NotAuthorized()
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    def retrieve(self, request, pk=None):
        perm = check_permision(request.user)
        if perm == 1:
            queryset = Student.objects.filter(reservation__bed__room__residence__manager=request.user,
                                              user__student=pk).prefetch_related(Prefetch('reservation_set', queryset=Reservation.objects.filter(Q(status=3) | Q(status=0))),
                                                                                 'user', 'sex', 'department').annotate(user_first_name=F('user__first_name'), user_last_name=F('user__last_name'), sex_desc=F('sex__description'), dep_desc=F('department__description')).distinct()
        elif perm == 0:
            queryset = Student.objects.filter(user_id=request.user,
                                              user__student=pk).prefetch_related(Prefetch('reservation_set', queryset=Reservation.objects.filter(Q(status=3) | Q(status=0))),
                                                                                 'user', 'sex', 'department').annotate(user_first_name=F('user__first_name'), user_last_name=F('user__last_name'), sex_desc=F('sex__description'), dep_desc=F('department__description')).distinct()
        else:
            raise NotAuthorized()
        data = [
            {
                "document": student.document,
                "document_type": Student.DOCUMENT[0][1] if student.document_type == Student.DOCUMENT[0][0] else Student.DOCUMENT[1][1],
                "image": student.image.url if student.image else None,
                "user_id":student.user.id,
                "user_first_name": student.user.first_name,
                "user_last_name": student.user.last_name,
                "user_mail": student.user.email,
                "sex_desc": student.sex.description,
                "birth_date": student.birth_date,
                "cel": student.cel,
                "medical_soc": student.medical_soc,
                "allergies": student.allergies,
                "dep_desc": student.department.description if student.department else None,
                "tutor": TutorSerializer(student.tutor_set, many=True).data,
                "reservation": ReservationSerializer(student.reservation_set.all(), many=True).data
            }
            for student in queryset]
        return Response(data)

    def update(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        stud = self.get_object()
        stud_ef = Student.objects.get(user=request.user)
        if perm == 0 and stud_ef == stud:
            request.data.update({'user': request.user.id})
            document = request.data.get('document')
            document_type = request.data.get('document_type')
            validate_document_proc(self, request, document, document_type)
            if not 'sex' in request.data:
                if self.get_object().sex is not None:
                    request.data.update({'sex': self.get_object().sex.id})
            if not 'document_type' in request.data:
                if self.get_object().document_type is not None:
                    request.data.update(
                        {'document_type': self.get_object().document_type})
            elif 'document_type' in request.data:
                for doc_type in Student.DOCUMENT:
                    if doc_type[1] == request.data.get('document_type'):
                        final_document_type = doc_type[0]
                        request.data.update(
                            {'document_type': final_document_type})
            return super().update(request, *args, **kwargs)
        else:
            return Response(data={"detail": "You are not authorized to access"},
                            status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['GET'], url_path='month-report')
    def yearmonth_status(self, request):
        today = timezone.now()
        perm = check_permision(request.user)
        year_month = request.GET.get("year_month")
        try:
            if perm == 1:
                reservations = Reservation.objects.filter(
                    (Q(status=Bed.ACTIVE) | Q(status=Bed.INACTIVE)), bed__room__residence__manager=self.request.user, date_from__lte=today).distinct('student__id')
                data = [
                    {
                        "reservation_number": res.reservation_number,
                        "student_id": res.student.id,
                        "student_first_name": res.student.user.first_name,
                        "student_last_name": res.student.user.last_name,
                        "payment": PaymentIdSerializer(res.payment_set.filter(year_month=year_month), many=True).data
                    } for res in reservations]
                return Response(data, status=status.HTTP_200_OK)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)


def validate_document_proc(self, request, document, document_type):
    if document is not None:
        if document_type is not None:
            doc_type = validate_document(document, document_type)
            if not doc_type:
                raise Response(data={"detail": "The document provided is not valid."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(data={"detail": "The document type is required."},
                            status=status.HTTP_400_BAD_REQUEST)
    elif self.get_object().document is not None:
        request.data.update({'document': self.get_object().document})


def validate_document(document, document_type):
    uruguayan_doc = UruguayanDocument()
    document_type_new = None
    
    if document.isnumeric() and len(document) == 8:
        document_display_type = document_type
        for doc_type in Student.DOCUMENT:
            if doc_type[0] == document_display_type:
                document_type_new = doc_type[0]
        if document_type_new is None:
            raise DocumentTypeInvalid('acaaaaaaaaa')
        is_registered = Student.objects.filter(
            document=document).count()
        if is_registered > 0:
            raise DocumentAlreadyRegistered(
                "The document provided is already registered")
        else:
            if document_type_new == Student.URUGUAYAN:
                validated = uruguayan_doc.validate_ci(int(document))
                if validated:
                    return document_type_new
                else:
                    raise DocumentNotValid(
                        "The document provided is not valid")
            elif document_type_new == Student.PASSPORT:
                return document_type_new
            elif document_type_new not in Student.DOCUMENT.get_field_by_name():
                raise DocumentTypeInvalid('aca')
    else:
        raise DocumentNotValid("The document provided is not valid")


class TutorViewSet(viewsets.ModelViewSet):
    queryset = Tutor.objects.all()
    serializers = {
        'list': TutorSerializer,
        'create': TutorCreateSerializer,
        'delete': TutorCreateSerializer,
        'default': TutorSerializer,
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action,
                                    self.serializers.get('default'))

    def create(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        try:
            if perm == 0:
                student = Student.objects.filter(user=request.user)
                if student.count() > 1:
                    raise MultipleAssociations(
                        "Exists multiple associations for this student")
                elif student.count() == 1:
                    student_id = student.first().id
                    if request.data.get('student') == student_id:
                        if 'relation' in request.data:
                            rel_desc = request.data.get('relation')
                            for elem in RELATION_CHOICES:
                                if elem[1] == rel_desc:
                                    request.data['relation'] = elem[0]
                                    try:
                                        return super().create(request)
                                    except KeyError:
                                        return Response(data={"detail": "The tutor cannot be created if student does not exist."},
                                                        status=status.HTTP_400_BAD_REQUEST)

                            else:
                                return Response(data={"detail": "Relation description is not valid"},
                                                status=status.HTTP_400_BAD_REQUEST)
                    else:
                        raise ObjectDoesntExistOrNotAuthorized(
                            "The student is not registered or you are not authorized to access")
                else:
                    raise ObjectDoesntExistOrNotAuthorized(
                        "The student is not registered or you are not authorized to access")
            else:
                return Response(data={"detail": "You are not authorized to access"},
                                status=status.HTTP_401_UNAUTHORIZED)
        except ObjectDoesntExistOrNotAuthorized:
            return Response(data={"detail": "The object does not exist or you are not authorized to access"},
                            status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response(data={"detail": "There is an error in the foreign keys yo need"},
                            status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        instance = self.get_object()
        perm = check_permision(request.user)
        if perm == 0:
            student = Student.objects.filter(user=request.user)
            if student.count() > 1:
                raise MultipleAssociations(
                    "Exists multiple associations for this student")
            elif student.count() == 1:
                student_id = student.first().id
                student_logged = instance.student.id
                if student_logged == student_id:
                    super().destroy(request, format)
                    return Response(data={"detail": "Object eliminated"},
                                    status=status.HTTP_200_OK)
                else:
                    raise ObjectDoesntExistOrNotAuthorized(
                        "The student is not registered or you are not authorized to access")
        else:
            raise NotAuthorized("The user logged is not authorized to access")


class RelationAPIView(APIView):
    def get(self, request):
        data = [
            {
                "relation_id": relation[0],
                "relation_description":relation[1]
            }
            for relation in RELATION_CHOICES]
        return Response(data)


class DocumentNotValid(Exception):
    pass


class DocumentAlreadyRegistered(Exception):
    pass


class DocumentTypeInvalid(Exception):
    pass
