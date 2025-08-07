from functools import wraps

from django.shortcuts import redirect


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
            return redirect("mainwebsite:passkey_login")

    return _wrapped_view
