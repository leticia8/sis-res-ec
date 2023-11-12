# Generated by Django 3.2.2 on 2021-09-27 11:58

import django.contrib.gis.db.models.fields
import django.contrib.gis.geos.point
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('street', models.CharField(max_length=200)),
                ('number', models.IntegerField()),
                ('apartment', models.CharField(blank=True, max_length=8, null=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(blank=True, default=django.contrib.gis.geos.point.Point(0.0, 0.0), geography=True, null=True, srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='Sex',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='Zone',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Institute',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=100)),
                ('contact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.address')),
            ],
        ),
        migrations.AddField(
            model_name='address',
            name='zone',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.zone'),
        ),
    ]