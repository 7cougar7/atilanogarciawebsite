# Generated by Django 4.2.6 on 2023-11-03 09:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainwebsite', '0004_alter_phonenumber_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonecallsession',
            name='call_sid',
            field=models.CharField(blank=True, default='', max_length=50, null=True),
        ),
    ]
