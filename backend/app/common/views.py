from common.models import Department, Zone, Institute, Sex, Message
from common.serializers import ZoneSerializer, InstituteSerializer, SexSerializer, DepartmentSerializer, MessageSerializer
from student.models.student import Student
from user.models import Notification
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django.db.models.query_utils import InvalidQuery
from collections import defaultdict
import random
import datetime
import math


class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer


class SexViewSet(viewsets.ModelViewSet):
    queryset = Sex.objects.all()
    serializer_class = SexSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class InstituteViewSet(viewsets.ModelViewSet):
    queryset = Institute.objects.all()
    serializer_class = InstituteSerializer


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def create(self, request, *args, **kwargs):
        perm = check_permision(request.user)
        try:
            if perm == 1 or perm == 0:
                to = request.data.get('to_mes')
                request.data.update({'from_mes': request.user.id})
                if to == request.user.id:
                    raise InvalidQuery()
                return super().create(request, *args, **kwargs)
            else:
                raise NotAuthorized()

        except NotAuthorized:
            return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        perm = check_permision(request.user)
        try:
            if perm == 1 or perm == 0:
                queryset = Message.objects.filter(
                    Q(from_mes=request.user) | Q(to_mes=request.user)).order_by('date_created')
                user_to = defaultdict(list)
                for element in queryset:
                    other_us = element.from_mes.id if element.from_mes != request.user else element.to_mes.id
                    from user.views import UserViewSet
                    manager_from= UserViewSet.check_role_method(element.from_mes)
                    manager_to= UserViewSet.check_role_method(element.to_mes)
                    data = {
                        'id': element.id,
                        'message': element.message,
                        'date_created': element.date_created,
                        'date_viewed': element.date_viewed,
                        'user_from_id': element.from_mes.id,
                        'user_from_first_name': element.from_mes.first_name,
                        'user_from_email': element.from_mes.email,
                        'user_to_id': element.to_mes.id,
                        'user_to_first_name': element.to_mes.first_name,
                        'user_to_email': element.to_mes.email,
                        'residence_from': manager_from,
                        'residence_to': manager_to

                    }
                    (user_to[other_us]).append(data)
                formatted = [{'other_user': key, 'conversation': value}
                             for key, value in user_to.items()]
                return Response(formatted)
            else:
                raise NotAuthorized()

        except NotAuthorized:
            return Response(data={"detail": "The association does not exist or you are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        today = timezone.now()
        perm = check_permision(request.user)
        instance = self.get_object()
        try:
            if perm == 1 or perm == 0:
                if instance.to_mes == request.user:
                    instance.date_viewed = today
                    instance.save()
                    serializer = MessageSerializer(
                        data=instance)
                    serializer.is_valid()
                    return Response(data=serializer.data)
                else:
                    raise NotAuthorized()
            else:
                raise NotAuthorized()

        except NotAuthorized:
            return Response(data={"detail": "You are not authorized to access."},
                            status=status.HTTP_400_BAD_REQUEST)

# This code was obtained from https://github.com/francocorreasosa/ci_py


class UruguayanDocument:
    def get_validation_digit(self, ci):
        a = 0
        i = 0
        if len(str(ci)) <= 6:
            for i in range(len(ci), 7):
                ci = '0' + ci
                i = i + 1

        for i in range(0, 7):
            a += (int("2987634"[i]) * int(str(ci)[i])) % 10
            i = i + 1

        if a % 10 == 0:
            return 0
        else:
            return 10 - a % 10

    def clean_ci(self, ci):
        return int(str(ci).replace("-", "").replace('.', ''))

    def validate_ci(self, ci):
        ci = self.clean_ci(ci)
        dig = int(str(ci)[int(len(str(ci))) - 1])
        return dig == self.get_validation_digit(ci)

    def random_ci(self):
        ci = random.randint(0000000, 9999999)
        return int(str(ci) + str(self.get_validation_digit(ci)))

##


def obtain_month_year(year_month):
    year_month_int = int(year_month)
    month = year_month_int % 100
    year = math.trunc(year_month_int / 100)
    return month, year


def check_permision(user):
    if user.groups.filter(name="Manager").count() > 0:
        return 1
    elif user.groups.filter(name="Student").count() > 0:
        return 0
    else:
        return -1


def obtain_month_cleaned(month_in):
    if month_in <= 9:
        month_str = '0' + str(month_in)
    else:
        month_str = str(month_in)
    return month_str


def construct_month_year(year, month_str):
    return int(str(year) + month_str)


def calculate_price(price, date_from, date_until, yearmonthdict):
    year = date_from.year
    if date_from.year == date_until.year:
        yearmonthdict = obtain_income(
            price, date_from, date_until, yearmonthdict, year)

    elif date_from.year < date_until.year:
        for year_in in range(date_from.year, date_until.year + 1):
            if date_until.year > year_in:
                date_to_be_until = datetime.datetime(
                    year=year_in, month=12, day=31).date()
            else:
                date_to_be_until = date_until
            yearmonthdict = obtain_income(
                price, date_from, date_to_be_until, yearmonthdict, year_in)
    return yearmonthdict


def obtain_income(price, date_from, date_until, yearmonthdict, year):
    if date_from.month == date_until.month:
        dayss = obtain_days(date_from.month, date_from.year)
        month_str = obtain_month_cleaned(date_from.month)
        yearmonth = construct_month_year(date_from.year, month_str)
        yearmonthdict[yearmonth] += (
            (date_until - date_from).days + 1) * price / dayss
    elif date_from.month != date_until.month:
        for month_in in range(date_from.month, date_until.month + 1):
            days = obtain_days(month_in, date_from.year)
            month_str = obtain_month_cleaned(month_in)
            yearmonth = construct_month_year(year, month_str)
            if month_in == date_from.month:
                date_to_be_until = datetime.datetime(
                    year=date_from.year, month=date_from.month, day=days).date()
                yearmonthdict[yearmonth] += ((date_to_be_until - date_from).days +
                                             1) * price / days
            elif month_in == date_until.month:
                date_to_be_from = datetime.datetime(
                    year=date_until.year, month=date_until.month, day=1).date()

                yearmonthdict[yearmonth] += ((date_until - date_to_be_from).days +
                                             1) * price / days
            else:
                yearmonthdict[yearmonth] += price
    return yearmonthdict


def obtain_days(month, year):
    if month in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    elif month in [4, 6, 9, 11]:
        return 30
    elif month == 2:
        if (year % 400 == 0 or (year % 100 != 0) and (year % 4 == 0)):
            return 29
        else:
            return 28


def calculate_year_month(year_from, year_until):
    year_list = list(range(year_from, year_until + 1))
    month_list = ['01', '02', '03', '04', '05',
                  '06', '07', '08', '09', '10', '11', '12']
    cartesian_list = []
    for year in year_list:
        for month in month_list:
            res = int(str(year) + month)
            cartesian_list.append(res)
    return cartesian_list


def check_student_exists(user_id):
    stud = Student.objects.get(user__id=user_id)
    return stud


class NotificationAPIView(APIView):
    def get(self, request):
        data = [
            {
                "notification_id": notification[0],
                "notification_description":notification[1]
            }
            for notification in Notification.NOTIFICATION_STATUS]
        return Response(data)


class NoActiveAssociation(Exception):
    pass


class InactiveElement(Exception):
    pass


class NotAuthorized(Exception):
    pass


class ObjectDoesntExistOrNotAuthorized(Exception):
    pass
