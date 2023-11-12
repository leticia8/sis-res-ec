from reservation.models.payment import Payment
from reservation.models.reservation import Reservation, Comment, ServiceOffered, ServiceConsumed
from residence.models.serviceoffered import ServiceOffered
from common.models import ServiceType
from rest_framework import serializers


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'student', 'date_from', 'date_until',
                  'bed', 'status', 'reservation_number', 'contract']

    def validate(self, data):
        if (data['date_from'] > data['date_until']):
            raise serializers.ValidationError("finish must occur after start")
        return data


class ReservationUploadContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['contract']


class PaymentUpdateReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['file']


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = '__all__'


class PaymentIdSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = ['id', 'amount']


class PaymentListSerializer(serializers.ModelSerializer):
    reservation = ReservationSerializer

    class Meta:
        model = Payment
        fields = ('id', 'reservation', 'amount', 'year_month', 'file',
                  'payment_date', 'status', 'observations')


class PaymentCreateStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'amount', 'year_month', 'file',
                  'payment_method', 'payment_date')


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'description']


class ServiceOfferedSerializer(serializers.ModelSerializer):
    service = ServiceTypeSerializer(many=False)

    class Meta:
        model = ServiceOffered
        fields = ['service']


class ServiceConsumedSerializer(serializers.ModelSerializer):
    service = ServiceOfferedSerializer()

    class Meta:
        model = ServiceConsumed
        fields = ['id', 'date_created', 'amount',
                  'payment_date', 'date_cancelled', 'observations', 'service', ]


class ServiceConsumedCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ServiceConsumed
        fields = ['id', 'date_created', 'amount',
                  'payment_date', 'date_cancelled', 'observations', 'service', 'reservation']


class CommentListSerializer(serializers.ModelSerializer):
    reservation = ReservationSerializer(many=False)

    class Meta:
        model = Comment
        fields = ('score', 'review', 'reservation_id', 'reservation')


class CommentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Comment
        fields = ('score', 'review', 'reservation')
