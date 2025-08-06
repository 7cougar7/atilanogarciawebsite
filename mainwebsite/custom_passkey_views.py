from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity,
    AttestationConveyancePreference,
    AttestedCredentialData,
)
from fido2.utils import websafe_decode, websafe_encode
from passkeys.models import UserPasskey as Passkey
import json


def get_fido2_server(request):
    rp_id = request.get_host().split(":")[0]
    return Fido2Server(
        PublicKeyCredentialRpEntity(id=rp_id, name="Atilano Garcia Website"),
        attestation=AttestationConveyancePreference.NONE,
    )


def get_user_credentials(user):
    return [
        {"type": "public-key", "id": websafe_decode(key.credential_id)}
        for key in Passkey.objects.filter(user=user)
    ]


def dynamic_reg_begin(request):
    if not request.user.is_authenticated:
        login_url = (
            f"{reverse('admin:login')}?next={reverse('mainwebsite:passkey_login')}"
        )
        return JsonResponse(
            {
                "error": "You must be logged in to register a new passkey.",
                "login_url": login_url,
            },
            status=401,
        )

    server = get_fido2_server(request)
    user = request.user

    registration_data, state = server.register_begin(
        {
            "id": user.username.encode("utf-8"),
            "name": user.get_full_name(),
            "displayName": user.username,
        },
        get_user_credentials(user),
    )

    request.session["passkey_registration_state"] = state
    return JsonResponse(dict(registration_data))


@require_POST
@login_required
def dynamic_reg_complete(request):
    try:
        data = json.loads(request.body)
        server = get_fido2_server(request)
        state = request.session.pop("passkey_registration_state")

        credential = server.register_complete(state, data)

        Passkey.objects.create(
            user=request.user,
            credential_id=data["id"],
            token=websafe_encode(credential.credential_data),
            name=f"Passkey-{data['id'][:8]}",
        )

        return JsonResponse({"status": "OK"})
    except Exception as e:
        return JsonResponse({"error": f"Registration failed: {e}"}, status=400)


@csrf_exempt
def dynamic_auth_begin(request):
    server = get_fido2_server(request)
    auth_data, state = server.authenticate_begin()
    request.session["passkey_authentication_state"] = state
    return JsonResponse(dict(auth_data))


@require_POST
@csrf_exempt
def custom_auth_complete(request):
    try:
        data = json.loads(request.body)
        credential_id = data["id"]

        server = get_fido2_server(request)
        state = request.session.pop("passkey_authentication_state")

        passkey = Passkey.objects.get(credential_id=credential_id)
        user = passkey.user

        # Correctly load all of the user's passkeys for verification
        credentials = [
            AttestedCredentialData(websafe_decode(key.token))
            for key in Passkey.objects.filter(user=user)
        ]

        server.authenticate_complete(state, credentials, data)

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["passkey_authenticated"] = True
        request.session.modified = True

        return JsonResponse(
            {
                "status": "OK",
                "debug": {
                    "user_authenticated": request.user.is_authenticated,
                    "session_keys": list(request.session.keys()),
                },
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "error": f"Authentication failed: {e}",
                "debug": {
                    "user_authenticated": request.user.is_authenticated,
                    "session_keys": list(request.session.keys()),
                },
            },
            status=400,
        )
