import logging
from django.templatetags.static import static
from django_twilio.decorators import twilio_view
from django_twilio.request import decompose
from twilio.twiml.voice_response import VoiceResponse
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from mainwebsite import models

logger = logging.getLogger(__name__)

def start_two_way(request: HttpRequest)  -> HttpResponse:
    if request.method == 'POST':
        caller_phone_number = request.POST['caller_phone_number']
        callee_phone_number = request.POST['callee_phone_number']
        if caller_phone_number and callee_phone_number:
            try:
                session = iniate_phone_caller(caller_phone_number)
                iniate_phone_callee(callee_phone_number, session)
                return HttpResponse(status=200)
            except Exception as error:
                logger.exception(error)
                return HttpResponse(status=400)
        return HttpResponse(status=400)
    return HttpResponse(status=400)


def get_phone_number_model(phone_number: str) -> models.PhoneNumber:
    phone_number_model = models.PhoneNumber.objects.filter(phone_number=phone_number)
    if not phone_number_model:
        phone_number_model = models.PhoneNumber(phone_number=phone_number)
        phone_number_model.save()
    else:
        phone_number_model = phone_number_model.first()
    return phone_number_model


def iniate_phone_caller(caller_phone_number: str) -> models.PhoneCallSession:
    caller_phone_number_model = get_phone_number_model(caller_phone_number)
    
    phone_call_session = models.PhoneCallSession(caller=caller_phone_number_model)
    phone_call_session.save()
    
    #TODO Add like actual calling logic
    
    return phone_call_session
    

def iniate_phone_callee(callee_phone_number: str, session: models.PhoneCallSession) -> None:
    
    callee_phone_number_model = get_phone_number_model(callee_phone_number)
    
    session.set_callee(callee_model=callee_phone_number_model)
    
    #TODO Add like actual calling logic
    
    
