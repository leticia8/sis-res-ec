# Generated by Django 3.2.2 on 2021-09-30 10:27

from django.db import migrations, models
import student.models.student


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=student.models.student.profile_path),
        ),
    ]
