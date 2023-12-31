# Generated by Django 3.2.2 on 2021-09-27 11:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document', models.CharField(max_length=200, unique=True)),
                ('document_type', models.IntegerField(choices=[(1, 'UY'), (2, 'PA')])),
                ('image', models.ImageField(blank=True, null=True, upload_to='media/profiles')),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('cel', models.CharField(blank=True, max_length=20, null=True)),
                ('medical_soc', models.CharField(blank=True, max_length=200, null=True)),
                ('allergies', models.CharField(blank=True, max_length=200, null=True)),
                ('department', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='common.department')),
                ('sex', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.sex')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Tutor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('relation', models.IntegerField(choices=[(1, 'Mother'), (2, 'Father'), (3, 'Other relative'), (4, 'Tutor not relative'), (5, 'Other person')])),
                ('cel', models.CharField(max_length=20)),
                ('address', models.CharField(blank=True, max_length=200, null=True)),
                ('data', models.CharField(blank=True, max_length=200, null=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='student.student')),
            ],
        ),
    ]
