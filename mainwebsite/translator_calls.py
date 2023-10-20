import logging
from django.templatetags.static import static
from django_twilio.decorators import twilio_view
from django_twilio.request import decompose
from twilio.twiml.voice_response import VoiceResponse
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
import models

@twilio_view
def iniate_caller_phone_call(request: HttpRequest) -> HttpResponse:
    pass
    # twilio_request = decompose(request)
    # models.PhoneNumber.objects.filter(phone_number=twilio_request.from)
    # response = VoiceResponse()
    # response.say("hit")
    # return response