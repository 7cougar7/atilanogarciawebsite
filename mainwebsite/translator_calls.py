import logging
from babel import Locale
from django_twilio.decorators import twilio_view
from twilio.twiml.voice_response import VoiceResponse, Start, Stream
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from mainwebsite import models
from googletrans import Translator
from twilio.rest import Client
import atilanogarciawebsite.settings as settings
from django.contrib.sites.shortcuts import get_current_site

logger = logging.getLogger(__name__)
translator = Translator()
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def start_two_way(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        caller_phone_number = request.POST["caller_phone_number"]
        callee_phone_number = request.POST["callee_phone_number"]
        if caller_phone_number and callee_phone_number:
            try:
                session = setup_caller(caller_phone_number)
                setup_callee(callee_phone_number, session)
                initiate_phone_call(
                    request=request,
                    session_model=session,
                    phone_number_model=session.caller,
                )

                # initiate_phone_call(
                #     request=request,
                #     session_model=session,
                #     phone_number_model=session.callee,
                # )
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


def establish_language_menu(
    request: HttpRequest,
    twiml: VoiceResponse,
    phone_number_model: models.PhoneNumber,
):
    twiml.say("You do not have a set language yet")

    try:
        with twiml.gather(
            action=f'{request.build_absolute_uri(reverse("set_language"))}?phone_number_model_id={phone_number_model.id}',
            numDigits=1,
            timeout=20,
        ) as gather:
            for index, lang_code in enumerate(models.AVAILABLE_LANGUAGES):
                split_code = lang_code.split("-")
                locale = Locale(
                    language=split_code[0],
                    territory=split_code[1] if len(split_code) == 2 else "",
                )

                prompt = f"Press {index+1} to set your language to"

                translated_prompt = translator.translate(
                    text=prompt, dest=models.get_gtrans_code(lang_code)
                )

                gather.say(
                    language=lang_code,
                    message=f"{translated_prompt.text} {locale.display_name}.",
                )
            gather.say("Or press pound to repeat this menu.")
    except Exception as error:
        logger.error(error)
        print(error)

    return twiml


@twilio_view
def set_language(request: HttpRequest) -> HttpResponse:
    response = VoiceResponse()
    try:
        selection = int(request.POST.get("Digits"))
        if selection > len(models.AVAILABLE_LANGUAGES):
            raise Exception

        phone_number_model_id = int(request.GET.get("phone_number_model_id"))
        print(f"{phone_number_model_id=}")
        phone_number_model = models.PhoneNumber.objects.get(id=phone_number_model_id)
    except Exception as error:
        response.say("Please select an option from the list.")
        logger.error(error)
        print(error)
    else:
        try:
            phone_number_model.language = models.AVAILABLE_LANGUAGES[selection - 1]
            phone_number_model.save()
        except Exception as error:
            logger.error(error)
            print(error)

    return str(response)


def initiate_phone_call(
    request: HttpRequest,
    session_model: models.PhoneCallSession,
    phone_number_model: models.PhoneNumber,
):
    twiml = VoiceResponse()
    start = Start()
    protocol = "ws"
    if request.build_absolute_uri()[:5] == "https":
        protocol += "s"

    websocket_url = f"{protocol}://{get_current_site(request)}/ws/call/"
    print(f"{websocket_url=}")
    stream = Stream(url=websocket_url)
    stream.parameter(name="phoneNumber", value=phone_number_model.phone_number)
    start.append(stream)

    twiml.append(start)

    if not phone_number_model.language:
        establish_language_menu(request, twiml, phone_number_model)
    else:
        message_to_translate = "Hello, world!"
        translated_message = translator.translate(
            message_to_translate, dest=phone_number_model.gtrans_lang_code
        ).text

        twiml.say(
            language=phone_number_model.twilio_lang_code,
            message=translated_message,
        )
    twiml.pause(10)

    call = client.calls.create(
        twiml=twiml,
        to=str(phone_number_model.phone_number),
        from_="+18445680811",
    )

    if session_model.callee == phone_number_model:
        session_model.callee_sid = call.sid
    else:
        session_model.caller_sid = call.sid
    session_model.save()
    # return call
