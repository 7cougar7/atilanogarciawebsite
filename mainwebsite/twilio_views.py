import logging
from django.templatetags.static import static
from django_twilio.decorators import twilio_view
from twilio.twiml.voice_response import VoiceResponse
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

logger = logging.getLogger(__name__)
def get_menu_options():
    return {
        1: {
            'description': 'a dank beat',
            'sound_url': static("mainwebsite/music/swamp_remix.mp3")
            },
        2: {
            'description': 'hype music',
            'sound_url': static("mainwebsite/music/swamp_remix.mp3")
            },
        3: {
            'description': 'Taylor',
            'sound_url': static("mainwebsite/music/swamp_remix.mp3")
            },
        4: {
            'description': 'something crazy',
            'sound_url': ''
            }
    }

@twilio_view
def twilio_incoming(request: HttpRequest) -> HttpResponse:
    '''Respond to incoming phone calls with a 'Hello world' message'''
    # Start our TwiML response
    response = VoiceResponse()
    try:
        response.say('Welcome to Tealow\'s Phone Application')
        with response.gather(
            action=reverse('twilio_menu_action'),
            numDigits=1,
            timeout=20,
        ) as gather:
            prompt = 'Please press'
            for key, info in get_menu_options().items():
                if key == list(get_menu_options().keys())[-1]:
                    prompt += ', or '
                prompt += f' {key} for {info["description"]}'
                if key != list(get_menu_options().keys())[-1]:
                    prompt += ','
                else:
                    prompt += '.'
            gather.say(prompt)
        response.say('We did not receive your selection')
        response.redirect('')
    except Exception as error:
        logger.error(error)

    return HttpResponse(str(response), content_type='text/xml')

@twilio_view
def twilio_menu_action(request: HttpRequest) -> HttpResponse:
    response = VoiceResponse()
    try:
        selection = int(request.POST.get('Digits'))
        if selection not in get_menu_options().keys():
            raise Exception
    except Exception:
        response.say('Please select an option from the list.')
        response.redirect(reverse('twilio_incoming'))
    
    else:
        if selection == 4:
            response.repeat(
                'Crazy? I was crazy once. \
                They locked me in a room. \
                A rubber room. \
                A rubber room with rats. \
                And rats make me crazy'
            )
        else:
            response.play(get_menu_options()[selection]['song_url'])
    
    return HttpResponse(str(response), content_type='text/xml')