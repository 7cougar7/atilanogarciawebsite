"""
ASGI config for atilanogarciawebsite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from atilanogarciawebsite.translator_consumers import CallConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atilanogarciawebsite.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(
            [
                path("ws/call/", CallConsumer.as_asgi()),
            ]
        ),
    }
)
