from django.http import JsonResponse
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.utils import timezone
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity,
    AttestationConveyancePreference,
    UserVerificationRequirement,
    AttestedCredentialData,
)
from fido2.utils import websafe_decode, websafe_encode
from passkeys.FIDO2 import fido2
from passkeys.models import UserPasskey as Passkey
import json

# This custom view is a patch to address a bug in django-passkeys==1.3.0.1
# where the original auth_complete view returns a Django User object on success
# instead of an HttpResponse. This causes a crash in Django's middleware
# (e.g., clickjacking middleware) which expects a response object.
# This override ensures a proper JsonResponse is always returned.


@require_POST
@never_cache
def custom_auth_complete(request):
    """Override of passkeys.FIDO2.auth_complete to ensure it returns a JsonResponse."""
    enable_json_mapping()
    host = request.get_host().split(":")[0]
    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    server = Fido2Server(rp_entity)

    try:
        data = json.loads(request.body)
        state = request.session.get("fido2_auth_state")
        credential_id = data["id"]

        # Find the passkey and user
        passkey = Passkey.objects.get(credential_id=credential_id)
        user = passkey.user
        credentials = [
            AttestedCredentialData(websafe_decode(p.token))
            for p in Passkey.objects.filter(user=user)
        ]

        # Complete authentication
        server.authenticate_complete(state, credentials, data)

        # Update last used timestamp
        passkey.last_used = timezone.now()
        passkey.save()

        # Log the user in
        login(request, passkey.user)
        request.session["passkey_authenticated"] = True
        return JsonResponse({"status": "OK", "message": "Login Successful"})
    except Exception as e:
        return JsonResponse({"status": "ERROR", "message": str(e)}, status=400)


# --- Multi-Domain FIDO2/WebAuthn Support ---
# The following views dynamically set the FIDO_SERVER_ID based on the request's domain.
# This is necessary because the application is served on multiple domains, and the
# FIDO2 Relying Party ID (RP ID) must match the domain the user is currently visiting.


def enable_json_mapping():
    """Enables the fido2 library's JSON mapping feature for proper response formatting."""
    try:
        fido2.features.webauthn_json_mapping.enabled = True
    except Exception:
        pass


@login_required
def dynamic_reg_begin(request):
    """Replicates the library's reg_begin logic with a dynamic FIDO server ID."""
    enable_json_mapping()
    host = request.get_host().split(":")[0]
    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    server = Fido2Server(rp_entity, attestation=AttestationConveyancePreference.NONE)

    user = request.user
    if not user.is_authenticated:
        return JsonResponse(
            {"status": "redirect", "redirectUrl": "/admin/login/"}, status=401
        )

    # Explicitly fetch the user's passkeys to avoid AttributeError
    user_passkeys = Passkey.objects.filter(user=user)

    # Exclude credentials that are already registered for this user
    exclude_credentials = [
        {"type": "public-key", "id": websafe_decode(key.token)} for key in user_passkeys
    ]

    registration_data, state = server.register_begin(
        {
            "id": user.username.encode("utf8"),
            "name": user.get_full_name(),
            "displayName": user.username,
        },
        exclude_credentials,
    )

    request.session["passkey_registration_state"] = state
    return JsonResponse(dict(registration_data))


@require_POST
@login_required
@never_cache
def dynamic_reg_complete(request):
    """Replicates the library's reg_complete logic with a dynamic FIDO server ID."""
    enable_json_mapping()
    host = request.get_host().split(":")[0]
    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    server = Fido2Server(rp_entity, attestation=AttestationConveyancePreference.NONE)

    try:
        data = json.loads(request.body)
        state = request.session.pop("passkey_registration_state")

        credential = server.register_complete(state, data)

        Passkey.objects.create(
            user=request.user,
            credential_id=websafe_encode(credential.credential_data.credential_id),
            token=websafe_encode(credential.credential_data),
            name=data.get(
                "name",
                f"Passkey-{websafe_encode(credential.credential_data.credential_id)[:8]}",
            ),
        )
        return JsonResponse({"status": "OK", "message": "Registration Successful"})
    except Exception as e:
        return JsonResponse(
            {"status": "ERROR", "message": f"Registration failed: {e}"},
            status=400,
        )


def dynamic_auth_begin(request):
    """Replicates the library's auth_begin logic with a dynamic FIDO server ID."""
    enable_json_mapping()
    host = request.get_host().split(":")[0]
    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    server = Fido2Server(rp_entity)

    username = request.GET.get("username")
    credentials = []
    if username:
        try:
            user = get_user_model().objects.get(username=username)
            credentials = [
                AttestedCredentialData(websafe_decode(p.token))
                for p in user.passkeys.all()
            ]
        except get_user_model().DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "User not found."}, status=404
            )

    auth_data, state = server.authenticate_begin(
        credentials, user_verification=UserVerificationRequirement.DISCOURAGED
    )

    request.session["fido2_auth_state"] = state
    return JsonResponse(dict(auth_data))
