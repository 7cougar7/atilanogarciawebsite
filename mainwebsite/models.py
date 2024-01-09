from django.contrib import admin
from django.db import models
from django.db.models import F
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField

AVAILABLE_LANGUAGES = ["en-US", "es-MX", "fr", "vi", "ko"]


def get_gtrans_code(locale):
    return locale.replace("-", "_")


def unique_short_code():
    while True:
        code = get_random_string(6)
        if not ShortenedUrl.objects.filter(shortened_url=code).exists():
            return code


class TranscribeAccessCode(models.Model):
    access_code = models.CharField(unique=True, max_length=25)

    number_of_calls = models.PositiveBigIntegerField()

    def increment_calls(self):
        self.number_of_calls = F("number_of_calls") + 1
        self.save(update_fields=["number_of_calls"])


class ShortenedUrl(models.Model):
    shortened_url = models.CharField(
        default=unique_short_code, unique=True, max_length=12
    )
    real_url = models.URLField()


class PhoneNumber(models.Model):
    phone_number = PhoneNumberField(null=False, blank=False, unique=True)
    language = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        default="",
        choices=zip(AVAILABLE_LANGUAGES, AVAILABLE_LANGUAGES),
    )

    def __str__(self):
        return str(self.phone_number)

    @property
    def gtrans_lang_code(self):
        return get_gtrans_code(self.language)

    @property
    def twilio_lang_code(self):
        return self.language


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "language"]


class PhoneCallSession(models.Model):
    caller = models.ForeignKey(
        PhoneNumber, null=True, on_delete=models.CASCADE, related_name="caller"
    )
    caller_sid = models.CharField(max_length=50, null=True, blank=True, default="")
    caller_is_active = models.BooleanField(default=False)

    callee = models.ForeignKey(
        PhoneNumber, null=True, on_delete=models.CASCADE, related_name="callee"
    )
    callee_sid = models.CharField(max_length=50, null=True, blank=True, default="")
    callee_is_active = models.BooleanField(default=False)

    @property
    def in_progress(self):
        return self.caller_is_active or self.callee_is_active

    def set_caller(self, caller_model: PhoneNumber):
        self.caller = caller_model
        self.save()

    def set_callee(self, callee_model: PhoneNumber):
        self.callee = callee_model
        self.save()

    def set_caller_active(self):
        if self.caller_is_active:
            raise Exception("Caller is already active")
        self.caller_is_active = True
        self.save()

    def set_callee_active(self):
        if self.callee_is_active:
            raise Exception("Callee is already active")
        self.callee_is_active = True
        self.save()


@admin.register(PhoneCallSession)
class PhoneCallSessionAdmin(admin.ModelAdmin):
    list_display = ["caller", "callee", "in_progress"]


admin.site.register(ShortenedUrl)
admin.site.register(TranscribeAccessCode)
