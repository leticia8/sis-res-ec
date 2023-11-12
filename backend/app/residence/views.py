from collections import defaultdict
from residence.models.residence import PaymentMethod, Residence, Room, Bed, BedPrice, BedType, ResidenceType
from residence.models.photo import Photo, PhotoHasTwoFks
from residence.serializers import ResidenceSerializer, ListResidenceSerializer, DetailResidenceSerializer, PhotoAllSerializer, PaymentMethodSerializer, BedSerializer, RoomSerializer, ResTypeSerializer, BedTypeSerializer
from reservation.models.reservation import InvalidRange, Reservation
from reservation.models.payment import Payment
from reservation import views
from common.models import Institute, Zone
from common.views import InactiveElement, NotAuthorized, ObjectDoesntExistOrNotAuthorized, check_permision, calculate_price, calculate_year_month
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Min, Avg, F, Exists, OuterRef, Count, Q, Sum
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.gis.measure import Distance
import datetime
from datetime import date

User = get_user_model()


class ResidenceViewSet(viewsets.ModelViewSet):
    today = timezone.now()
    queryset = Residence.objects.prefetch_related('address', 'type').annotate(min_bed_price=Min(
        'room__bed__bedprice__price'), rating=Avg('room__bed__reservation__comment__score', filter=Q(room__bed__reservation__comment__status=Bed.ACTIVE)), zone_desc=F('address__zone__description'),  type_desc=F('type__description')
    ).filter((Q(room__bed__bedprice__date_until__gte=today) | Q(room__bed__bedprice__date_until__isnull=True)))
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['address__zone', 'type_id']
    serializers = {
        'list': ListResidenceSerializer,
        'retrieve': DetailResidenceSerializer,
        'default': ResidenceSerializer
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action,
                                    self.serializers.get('default'))

    @action(detail=True, methods=['GET'], url_path='check-availability')
    def check_availability(self, request, pk=None):
        today = timezone.now()
        date_from = request.GET.get('date_from')
        date_until = request.GET.get('date_until')
        filter_params = dict(date_from__lte=date_until,
                             date_until__gte=date_from)
        beds = Bed.objects.exclude(Exists(Reservation.objects.filter(bed=OuterRef(
            'pk'), **filter_params, status__range=(Bed.PENDING, Bed.ACTIVE)))).filter((Q(bedprice__date_until__gte=today) | Q(bedprice__date_until__isnull=True)), room__residence=pk, status=Bed.ACTIVE).values(
                'room_id', 'type', 'type__description', 'bedprice__price').annotate(total=Count('*'), first_id=Min('id')).order_by('room_id').all()
        room_availability = serialize_availability(beds, pk)
        return Response(data=room_availability)

    @action(detail=False, methods=['GET'], url_path='filter-residence')
    def filter_residence(self, request, pk=None):
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        qs = Residence.objects.distinct('id')
        zone = self.request.GET.get('zone_id')
        type = self.request.GET.get('type_id')
        if type:
            qs = qs.filter(type_id=type)
        if zone:
            qs = qs.filter(address__zone_id=zone)
        if min_price:
            qs = qs.filter(room__bed__bedprice__date_until__isnull=True,
                           room__bed__bedprice__price__gte=min_price)
        if max_price:
            qs = qs.filter(room__bed__bedprice__date_until__isnull=True,
                           room__bed__bedprice__price__lte=max_price)
        serializer = ListResidenceSerializer(data=qs, many=True)
        serializer.is_valid()
        return Response(data=serializer.data)

    @action(detail=False, methods=['GET'], url_path='filter-distance')
    def filter_distance(self, request, pk=None):
        center_id = request.GET.get('centerid')
        distance = request.GET.get('distance')
        point = Institute.objects.filter(
            id=center_id).prefetch_related('Address').values('address__location')
        distances = obtain_distance(point, distance)
        serializer = ListResidenceSerializer(data=distances, many=True)
        serializer.is_valid()
        return Response(data=serializer.data)

    @action(detail=True, methods=['GET'], url_path='total-payments')
    def total_payments(self, request, pk=None):
        queryset = Payment.objects.filter(
            Q(reservation__status=Bed.ACTIVE) | Q(reservation__status=Bed.INACTIVE), status=Bed.ACTIVE, reservation__bed__room__residence__manager=request.user).values('year_month').annotate(all_payments=Sum('amount')).order_by('year_month')
        data = [
            {
                'year_month': element['year_month'],
                'all_payments': element['all_payments']
            } for element in queryset]

        return Response(data)

    @action(detail=True, methods=['GET'], url_path='month-income')
    def month_income(self, request, pk=None):
        yearmonth_from = request.GET.get('yearmonth_from')
        if yearmonth_from is None:
            yearmonth_from = 201901
        yearmonth_until = request.GET.get('yearmonth_until')
        if yearmonth_until is None:
            yearmonth_until = 202212
        month_from, year_from = views.obtain_month_year(yearmonth_from)
        month_until, year_until = views.obtain_month_year(yearmonth_until)
        queryset = Reservation.objects.filter((Q(status=Bed.ACTIVE) | Q(status=Bed.INACTIVE)), (Q(bed__bedprice__date_from__year__lte=year_until, bed__bedprice__date_from__month__lte=month_until) & (Q(bed__bedprice__date_until__year__gte=year_from,
                                                                                                                                                             bed__bedprice__date_until__month__gte=month_from) | Q(bed__bedprice__date_until__isnull=True))), bed__status=Bed.ACTIVE,
                                              bed__room__residence__manager=request.user,
                                              date_from__year__lte=year_until,
                                              date_until__year__gte=year_from
                                              ).distinct('id')
        cartesian_list = calculate_year_month(int(year_from), int(year_until))
        yearmonthdict = {k: 0 for k in cartesian_list}
        for reservation in queryset:
            reservation_date_from = reservation.date_from
            reservation_date_until = reservation.date_until
            bed_set = reservation.bed.bedprice_set.all()
            for bedprice in bed_set:
                bed_date_from = bedprice.date_from
                bed_date_until = bedprice.date_until
                if bed_date_until is None:
                    bed_date_until = reservation_date_until
                # CASO 1
                if bed_date_from < reservation_date_from and bed_date_until > reservation_date_from:
                    date_from = reservation_date_from
                    date_until = bed_date_until
                    yearmonthdict = calculate_price(bedprice.price,
                                                    date_from, date_until, yearmonthdict)
                # CASO 2
                elif (bed_date_from >= reservation_date_from and bed_date_until <= reservation_date_until):
                    date_from = bed_date_from
                    date_until = bed_date_until
                    yearmonthdict = calculate_price(bedprice.price,
                                                    date_from, date_until, yearmonthdict)
                # CASO 3
                elif (bed_date_from < reservation_date_from and bed_date_until > reservation_date_until):
                    date_from = reservation_date_from
                    date_until = reservation_date_until
                    yearmonthdict = calculate_price(bedprice.price,
                                                    date_from, date_until, yearmonthdict)
                # CASO 4
                elif bed_date_from < reservation_date_until and bed_date_until >= reservation_date_until:
                    date_from = bed_date_from
                    date_until = reservation_date_until
                    yearmonthdict = calculate_price(bedprice.price,
                                                    date_from, date_until, yearmonthdict)
        return Response(yearmonthdict)

    @action(detail=False, methods=['GET'], url_path='res-zone')
    def res_zone(self, request):
        queryset = Residence.objects.all().values('address__zone__id',
                                                  'address__zone__description').annotate(total_res=Count('id')).order_by('-total_res')
        zone_id_to_zone = {zone.id: zone for zone in Zone.objects.filter(
            id__in={element['address__zone__id'] for element in queryset})}
        data = [
            {
                'zone_name': element['address__zone__description'],
                'zone_id': element['address__zone__id'],
                'zone_photo': zone_id_to_zone[element['address__zone__id']].url,
                'amount_residences': element['total_res']

            } for element in queryset]

        return Response(data)

    @action(detail=False, methods=['GET'], url_path='best-rated')
    def best_rated(self, request):
        queryset = self.queryset.filter(rating__gte=4).order_by('-rating')
        serializer = ListResidenceSerializer(data=queryset, many=True)
        serializer.is_valid()
        return Response(data=serializer.data)


def obtain_distance(point, distance):
    clients_within_radius = Residence.objects.filter(address__location__distance_lt=(point,
                                                                                     Distance(m=distance)))
    return clients_within_radius


def serialize_availability(beds, pk):
    room_availability = defaultdict(dict)
    for room in Room.objects.filter(residence_id=pk):
        available_bed = [
            {
                'type': beed['type'],
                'description': beed['type__description'],
                'price': beed['bedprice__price'],
                'total': beed['total'],
                'fst_id_available': beed['first_id'],
            }
            for beed in beds if beed['room_id'] == room.id]
        room_availability[room.id] = {'id': room.id,
                                      'free_beds': sum(item['total'] for item in available_bed),
                                      'available_beds': available_bed
                                      }
    return room_availability


class PhotoAllViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoAllSerializer

    def create(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        res = None
        ro = None
        try:
            if perm == 1:
                residence = request.data.get('residence')
                room = request.data.get('room')
                if residence is not None:
                    res = Residence.objects.get(pk=residence)
                    if res.manager == request.user:
                        return super().create(request, *args, **kwargs)
                    else:
                        raise ObjectDoesntExistOrNotAuthorized()
                elif room is not None:
                    ro = Room.objects.get(pk=room)
                    if ro.residence.manager == request.user:
                        return super().create(request, *args, **kwargs)
                    else:
                        raise ObjectDoesntExistOrNotAuthorized()
                else:
                    raise ObjectDoesntExistOrNotAuthorized()
            else:
                raise ObjectDoesntExistOrNotAuthorized()
        except PhotoHasTwoFks:
            return Response(data={"detail": "The object could not have none or two foreign keys."},
                            status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesntExistOrNotAuthorized:
            return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer

    def list(self, request):
        if request.GET.get('residence'):
            resid = request.GET.get('residence')
            queryset = PaymentMethod.objects.filter(residence=resid)
            serializer = self.serializer_class(data=queryset, many=True)
            serializer.is_valid()
            return Response(data=serializer.data)
        else:
            return super().list(self, request)


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class BedViewSet (viewsets.ModelViewSet):
    queryset = Bed.objects.all()
    serializer_class = BedSerializer

    def list(self, request):
        today = timezone.now()
        queryset = Bed.objects.filter(
            room__residence__manager=self.request.user).prefetch_related('room__residence__manager')
        data = list()
        for bed in queryset:
            occup = Reservation.objects.filter(
                (Q(date_from__lte=today) & Q(date_until__gte=today) & (Q(status=Bed.INACTIVE) | Q(status=Bed.ACTIVE))), bed=bed.id).count()
            is_occup = True if occup >= 1 else False
            each = {
                "id": bed.id,
                "name": bed.name,
                "status": bed.status,
                "type": bed.type.id,
                "room": bed.room.id,
                "price": bed.actual_price if bed.actual_price is not None else 0,
                "occup": is_occup
            }
            data.append(each)
        return Response(data=data)

    def create(self, request, *args, **kwargs):
        perm = views.check_permision(request.user)
        try:
            if perm == 1:
                try:
                    price = request.data.get('bed_price')
                    room = request.data.get('room')
                    name = request.data.get('name')
                    type = request.data.get('type')
                    a_room = Room.objects.get(id=room)
                    bedtype = BedType.objects.get(pk=type)
                    if price is not None:
                        with transaction.atomic():
                            bed = Bed.objects.create(
                                name=name, room=a_room, type=bedtype)
                            BedPrice.objects.create(
                                price=price, date_from=timezone.now(), bed=bed)
                            return Response()
                    else:
                        raise ElementNotPresentInBody()
                except ElementNotPresentInBody:
                    return Response(data={"detail": "Bed Price is needed to create a bed."},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)

    def update(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                instance = self.get_object()
                if instance.room.residence.manager == request.user:
                    status2 = request.data.get('status')
                    if status2 < Bed.INACTIVE or status2 > Bed.ACTIVE:
                        raise InvalidRange()
                    instance.status = status2
                    instance.save()
                    serializer = BedSerializer(
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
        except InvalidRange:
            return Response(data={"detail": "The range of status is invalid."},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['PUT'], url_path='price')
    def price(self, request, pk=None):
        perm = check_permision(request.user)
        try:
            if perm == 1:
                is_active = check_bed_active(pk)
                if is_active:
                    bed = Bed.objects.get(pk=pk)
                    future_bedprice = request.data.get('future_bedprice')
                    bedprice_adj = future_bedprice * (1.02)
                    date_from_act_price = request.data.get(
                        'date_from_act_price')
                    date_until_prev_price = request.data.get(
                        'date_until_prev_price')
                    try:
                        actual_bedprice_count = BedPrice.objects.filter(
                            bed=bed, date_until=None).count()
                        if actual_bedprice_count == 0:
                            actual_bedprice = BedPrice.objects.filter(
                                bed=bed).order_by('-date_until').first()
                        elif actual_bedprice_count == 1:
                            actual_bedprice = BedPrice.objects.get(
                                bed=bed, date_until=None)
                        else:
                            raise ObjectDoesntExistOrNotAuthorized(
                                "The object doesn't exist or you are not authorized to access")
                        actual_date_from = actual_bedprice.date_from
                        if (actual_date_from > date.fromisoformat(date_until_prev_price)) or (date.fromisoformat(date_from_act_price) != (date.fromisoformat(date_until_prev_price) + datetime.timedelta(days=1))):
                            raise DateError()
                        actual_bedprice.date_until = date_until_prev_price
                        with transaction.atomic():
                            actual_bedprice.save()
                            BedPrice.objects.create(
                                price=bedprice_adj, date_from=date_from_act_price, bed=bed)
                            return Response()
                    except ObjectDoesntExistOrNotAuthorized:
                        return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                                        status=status.HTTP_400_BAD_REQUEST)
                    except BedPrice.DoesNotExist:
                        return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                                        status=status.HTTP_400_BAD_REQUEST)
                    except DateError:
                        return Response(data={"detail": "There is an error in date configutation. Periods cannot overlap."},
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    raise InactiveElement(
                        "The element you are trying to modify is not active")
            else:
                raise NotAuthorized("user not authorized")
        except NotAuthorized:
            return Response(data={"detail": "The user is not authorized to do this."},
                            status=status.HTTP_401_UNAUTHORIZED)
        except InactiveElement:
            return Response(data={"detail": "The element you are trying to modify is not active"},
                            status=status.HTTP_400_BAD_REQUEST)


class ResTypeViewSet(viewsets.ModelViewSet):
    queryset = ResidenceType.objects.all()
    serializer_class = ResTypeSerializer


class BedTypeViewSet(viewsets.ModelViewSet):
    queryset = BedType.objects.all()
    serializer_class = BedTypeSerializer


def check_bed_active(pk):
    bed = Bed.objects.get(pk=pk)
    status = bed.status
    if status == Bed.ACTIVE:
        return True
    else:
        return False


class ResidenceRegistrationAPIView(APIView):
    def post(self, request):
        subject = 'REGISTRO DE RESIDENCIA'
        nombre_residencia = request.data.get('name')
        direccion_residencia = request.data.get('address')
        email = request.data.get('email')
        phone = request.data.get('phone')
        final_text = 'nombre_residencia: {0} direccion: {1} email: {2} teléfono: {3}'.format(nombre_residencia,
                                                                                             direccion_residencia, email, phone)
        send_mail(subject, final_text,
                  settings.EMAIL_HOST_USER, [settings.EMAIL_REGISTER])
        return Response()


class DateError(Exception):
    pass


class ElementNotPresentInBody(Exception):
    pass
