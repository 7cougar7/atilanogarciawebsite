"""
Custom middleware for session security enhancements
"""

import time

from django.conf import settings


class PasskeySessionMiddleware:
    """
    Middleware to handle sliding expiration for passkey authentication sessions
    and enhanced session security.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Passkey session timeout (30 minutes)
        self.passkey_timeout = getattr(settings, "PASSKEY_SESSION_TIMEOUT", 1800)

    def __call__(self, request):
        # Check passkey authentication expiration before processing request
        self._check_passkey_expiration(request)

        response = self.get_response(request)

        # Update passkey authentication timestamp after successful request
        self._update_passkey_timestamp(request)

        return response

    def _check_passkey_expiration(self, request):
        """Check if passkey authentication has expired"""
        if request.session.get("passkey_authenticated"):
            last_activity = request.session.get("passkey_last_activity")

            if last_activity:
                current_time = time.time()
                if current_time - last_activity > self.passkey_timeout:
                    # Passkey session has expired
                    del request.session["passkey_authenticated"]
                    if "passkey_last_activity" in request.session:
                        del request.session["passkey_last_activity"]
                    if "webauthn_username" in request.session:
                        del request.session["webauthn_username"]

    def _update_passkey_timestamp(self, request):
        """Update the last activity timestamp for passkey authentication"""
        if request.session.get("passkey_authenticated"):
            request.session["passkey_last_activity"] = time.time()
