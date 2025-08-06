from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, AttestationConveyancePreference
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


@login_required
def dynamic_reg_begin(request):
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
    # This view will need to be implemented to handle the login completion
    # For now, it's a placeholder.
    return JsonResponse({"status": "OK"})
