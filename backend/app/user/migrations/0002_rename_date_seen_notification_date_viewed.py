# Generated by Django 3.2.2 on 2021-10-03 12:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='date_seen',
            new_name='date_viewed',
        ),
    ]