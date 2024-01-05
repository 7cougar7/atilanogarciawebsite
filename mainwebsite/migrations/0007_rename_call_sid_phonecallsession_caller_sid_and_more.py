# Generated by Django 4.2.6 on 2023-11-03 21:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainwebsite', '0006_alter_phonenumber_language'),
    ]

    operations = [
        migrations.RenameField(
            model_name='phonecallsession',
            old_name='call_sid',
            new_name='caller_sid',
        ),
        migrations.AddField(
            model_name='phonecallsession',
            name='callee_sid',
            field=models.CharField(blank=True, default='', max_length=50, null=True),
        ),
    ]
