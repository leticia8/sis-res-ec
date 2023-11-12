from .models import student
from rest_framework import serializers

from django.contrib.auth import get_user_model

User = get_user_model()


class StudentSerializer(serializers.ModelSerializer):
    user_first_name = serializers.ReadOnlyField()
    user_last_name = serializers.ReadOnlyField()
    sex_desc = serializers.ReadOnlyField()

    class Meta:
        model = student.Student
        fields = ['id', 'user_first_name',
                  'user_last_name', 'document', 'sex_desc', 'image']


class StudentOrigianSerializer(serializers.ModelSerializer):

    class Meta:
        model = student.Student
        fields = '__all__'


class TutorSerializer(serializers.ModelSerializer):
    rel_desc = serializers.CharField(source='get_relation_display')

    class Meta:
        model = student.Tutor
        fields = ['id', 'name', 'rel_desc', 'cel', 'address', 'data']

class TutorCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = student.Tutor
        fields = '__all__'
        

class StudentUpdateImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = student.Student
        read_only_fields = ['document', 'user__first_name']
        fields = ['image']
