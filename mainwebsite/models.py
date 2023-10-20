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

class PhoneNumber(models.Model):
    phone_number = PhoneNumberField(null=False, blank=False, unique=True)
    language = models.CharField(max_length=5, null=True, blank=True, default="")


class PhoneCallSession(models.Model):  
    caller = models.ForeignKey(PhoneNumber, null=True, on_delete=models.CASCADE, related_name='caller')
    caller_is_active = models.BooleanField(default=False)

    callee = models.ForeignKey(PhoneNumber, null=True, on_delete=models.CASCADE, related_name='callee')
    callee_is_active = models.BooleanField(default=False)
    
    @property
    def in_progress(self):
        return self.caller_is_active or self.callee_is_active    


admin.site.register(ShortenedUrl)
admin.site.register(PhoneNumber)
admin.site.register(PhoneCallSession)
