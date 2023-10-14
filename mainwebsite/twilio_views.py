
import logging
from django.templatetags.static import static
from django_twilio.decorators import twilio_view
from twilio.twiml.voice_response import VoiceResponse

logger = logging.getLogger(__name__)



@twilio_view
def twilio_incoming(request):
    """Respond to incoming phone calls with a 'Hello world' message"""
    # Start our TwiML response
    response = VoiceResponse()

    response.say('Welcome. Please listen to this dank. Ass. Beat.')
    response.play(static('mainwebsite/music/swamp_remix.mp3'))
    # Use <Record> to record the caller's message
    return str(response)
    
def twilio_outgoing(request):
    pass