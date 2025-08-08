from functools import wraps
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse

from .input_validation import get_safe_redirect_url


def passkey_login_required(view_func):
    """
    Decorator for views that checks that the user is logged in and has authenticated
    with a passkey in the current session.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.session.get(
            "passkey_authenticated"
        ):
            return view_func(request, *args, **kwargs)
        else:
            # Redirect to the unified login page with next parameter
            login_url = reverse("mainwebsite:login")

            # Use secure redirect validation for the next parameter
            raw_next_url = request.get_full_path()
            next_url = get_safe_redirect_url(
                raw_next_url, default_url="/", request=request
            )

            return redirect(f"{login_url}?{urlencode({'next': next_url})}")

    return _wrapped_view
