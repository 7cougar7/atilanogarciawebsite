import logging
from babel import Locale
from django.templatetags.static import static
from django_twilio.decorators import twilio_view
from django_twilio.request import decompose
from twilio.twiml.voice_response import VoiceResponse
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from mainwebsite import models
from googletrans import Translator
from twilio import twiml
from twilio.rest import Client
import atilanogarciawebsite.settings as settings

logger = logging.getLogger(__name__)
translator = Translator()
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def start_two_way(request: HttpRequest)  -> HttpResponse:
    if request.method == 'POST':
        caller_phone_number = request.POST['caller_phone_number']
        callee_phone_number = request.POST['callee_phone_number']
        if caller_phone_number and callee_phone_number:
            try:
                session = setup_caller(caller_phone_number)
                setup_callee(callee_phone_number, session)
                initiate_phone_call(
                    request=request,
                    phone_session_model=session,
                    phone_number_model=session.caller
                )
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


def setup_caller(caller_phone_number: str) -> models.PhoneCallSession:
    caller_phone_number_model = get_phone_number_model(caller_phone_number)
    
    phone_call_session = models.PhoneCallSession(caller=caller_phone_number_model)
    phone_call_session.save()
    
    return phone_call_session
    

def setup_callee(callee_phone_number: str, session: models.PhoneCallSession) -> None:
    
    callee_phone_number_model = get_phone_number_model(callee_phone_number)
    
    session.set_callee(callee_model=callee_phone_number_model)



def establish_language_menu(twiml):
    
    twiml.say('You do not have a set language yet')
    
    try:
        with twiml.gather(
            action=reverse('set_language'), #, kwargs={'phone_model_id': phone_number_model.id}),
            numDigits=1,
            timeout=20,
        ) as gather:
            for index, lang_code in enumerate(models.AVAILABLE_LANGUAGES):
                split_code = lang_code.split('-')
                locale = Locale(
                    language=split_code[0], 
                    territory=split_code[1] if len(split_code) == 2 else ''
                )
                
                prompt = f'Press {index+1} to set your language to {locale.display_name}.'
                print(prompt)
                gather.say(
                    language=lang_code,
                    message=translator.translate(
                        text=prompt, 
                        dest=models.get_gtrans_code(lang_code)
                    )
                )
            gather.say('Or press pound to repeat this menu.')
        twiml.redirect('')
    except Exception as error:
        logger.error(error)
        print(error)
    
    return twiml


def set_language(request: HttpRequest) -> HttpResponse:
    response = VoiceResponse()
    try:
        selection = int(request.POST.get('Digits'))
        if selection > len(models.AVAILABLE_LANGUAGES):
            raise Exception
        logger.info(f'{selection=}')
    except Exception as error:
        response.say('Please select an option from the list.')
        response.redirect(reverse('establish_language_menu'))
        logger.error(error)
        print(error)
    
    else:
        try:
            twilio_resp = decompose(request)
            logger.info(f'{twilio_resp=}')
            print(f'{twilio_resp=}')
        except Exception as error:
            logger.error(error)
            print(error)
    
    return str(response)


def initiate_phone_call(request: HttpRequest, phone_session_model: models.PhoneCallSession, phone_number_model: models.PhoneNumber):
    twiml = VoiceResponse()
    if not phone_number_model.language:
        # twiml.redirect(reverse('establish_language_menu'))
        establish_language_menu(twiml)
    else:
        message_to_translate = "Hello, world!"
        translated_message = translator.translate(
                message_to_translate,
                dest=phone_number_model.gtrans_lang_code
        ).text
        
        twiml.say(
            language=phone_number_model.twilio_lang_code,
            message=translated_message
        )
    
    print(str(twiml))
    call = client.calls.create(
        twiml=twiml,
        to=str(phone_number_model.phone_number),
        from_='+18445680811'
    )
    
    phone_session_model.call_sid = call.sid
    phone_session_model.save()
    
    if not phone_number_model.language:
        twiml.redirect(reverse('establish_language_menu'))
    
    return call
