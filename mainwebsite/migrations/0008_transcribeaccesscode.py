# Generated by Django 4.2.9 on 2024-01-09 02:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mainwebsite", "0007_rename_call_sid_phonecallsession_caller_sid_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TranscribeAccessCode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("access_code", models.CharField(max_length=25, unique=True)),
                ("number_of_calls", models.PositiveBigIntegerField()),
            ],
        ),
    ]