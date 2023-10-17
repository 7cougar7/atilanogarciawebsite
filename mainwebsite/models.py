from django.contrib import admin
from django.db import models
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField


def unique_short_code():
    while True:
        code = get_random_string(6)
        if not ShortenedUrl.objects.filter(shortened_url=code).exists():
            return code


class ShortenedUrl(models.Model):
    shortened_url = models.CharField(default=unique_short_code, unique=True, max_length=12)
    real_url = models.URLField()


class PhoneCall(models.Model):
    phone_number = PhoneNumberField(null=False, blank=False, unique=False)
    language = models.CharField()
    is_active = models.BooleanField(default=False)
    



admin.site.register(ShortenedUrl)
admin.site.register(PhoneCall)
