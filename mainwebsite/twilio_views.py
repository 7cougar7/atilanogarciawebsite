
import logging
from django.shortcuts import render
from django_twilio.decorators import twilio_view
from twilio.twiml.voice_response import VoiceResponse

logger = logging.getLogger(__name__)



@twilio_view
def twilio_incoming(request):
    """Respond to incoming phone calls with a 'Hello world' message"""
    # Start our TwiML response
    resp = VoiceResponse()

    # Read a message aloud to the caller
    resp.say("Hello world! Tealow testing")

    return str(resp)
    
def twilio_outgoing(request):
    pass