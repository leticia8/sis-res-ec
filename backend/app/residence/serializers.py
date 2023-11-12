from common.serializers import AddressSerializer
from common.models import Address
from user.serializers import UserSerializer
from residence.models.residence import PaymentMethod, Residence, Amenity, ResidenceType, Room, Bed, BedType
from residence.models.photo import Photo
from rest_framework import serializers


class ResidenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Residence
        fields = '__all__'


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['photo']


class RoomAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = '__all__'


class PhotoAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, source='photo_set')
    amenities = RoomAmenitySerializer(many=True, source='amenity')

    class Meta:
        model = Room
        fields = ['id', 'name', 'amenities', 'all_beds', 'photos']


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = '__all__'


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'


class ListResidenceSerializer(serializers.ModelSerializer):
    min_bed_price = serializers.ReadOnlyField()
    rating = serializers.ReadOnlyField()
    address = AddressSerializer()
    type_desc = serializers.ReadOnlyField()
    photo = PhotoSerializer(source='main')

    class Meta:
        model = Residence
        fields = ['id', 'name', 'type_desc', 'address', 'rating',
                  'photo', 'min_bed_price']
        required_fields = fields


class DetailResidenceSerializer(ListResidenceSerializer):
    address = AddressSerializer()
    rooms = RoomSerializer(many=True, source='room_set')
    photos = PhotoSerializer(many=True, source='photo_set')
    amenities = AmenitySerializer(many=True, source='amenity')
    type_desc = serializers.ReadOnlyField()
    manager = UserSerializer(many=False)

    class Meta:
        model = Residence
        fields = ['name', 'description',  'type_desc', 'manager', 'address', 'amenities',  'rating',
                  'photos', 'rooms', 'mail', 'tel', 'facebook', 'instagram']


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = '__all__'


class BedTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BedType
        fields = '__all__'


class ResTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidenceType
        fields = '__all__'
