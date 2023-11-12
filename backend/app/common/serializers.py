from common.models import Institute, Zone, Address, Sex, Department, Message
from rest_framework import serializers


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = '__all__'


class SexSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sex
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class AddressSerializer(serializers.ModelSerializer):
    zone = ZoneSerializer()

    class Meta:
        model = Address
        fields = '__all__'
        extra_fields = ['zone']


class InstituteSerializer(serializers.ModelSerializer):
    address = AddressSerializer()

    class Meta:
        model = Institute
        fields = '__all__'
        extra_fields = ['address']


class MessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Message
        fields = '__all__'
