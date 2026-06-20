"""
Dev-only test hook for the Playwright passkey E2E (tools/screenshots/auth_e2e.mjs).

The passkey register/login flows can't be exercised by a browser without an
authenticated session, so this exposes a single setup endpoint that logs in a fixed
test user ("e2euser") and grants the magic-link flag the registration page requires.

It is gated behind BOTH DEBUG and the E2E_TESTING env var, so it is unreachable in
production (DEBUG is False there) and even in dev unless explicitly enabled.
"""

import os

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, JsonResponse

E2E_USERNAME = "e2euser"


def e2e_enabled():
    return settings.DEBUG and os.environ.get("E2E_TESTING") == "1"


def auth_setup(request):
    if not e2e_enabled():
        return HttpResponseForbidden("E2E hooks are disabled")
    user, _ = User.objects.get_or_create(username=E2E_USERNAME)
    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
    request.session["magic_link_verified"] = True
    return JsonResponse({"ok": True, "username": E2E_USERNAME})
