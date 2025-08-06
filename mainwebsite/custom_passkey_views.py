from django.http import JsonResponse
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
import cbor2
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
import logging

logger = logging.getLogger(__name__)

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
    origin = request.headers.get("Origin")
    logger.info(
        f"[custom_auth_complete] Received request. Host: '{host}', Origin header: '{origin}'"
    )

    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    logger.info(
        f"[custom_auth_complete] Constructed RP Entity: id='{rp_entity.id}', name='{rp_entity.name}'"
    )

    server = Fido2Server(rp_entity)

    try:
        data = json.loads(request.body)
        logger.info(f"[custom_auth_complete] Request body data: {data}")
        state = request.session.get("fido2_auth_state")
        logger.info(f"[custom_auth_complete] Retrieved state from session: {state}")

        credential_id = data["credentialId"]

        # Find the passkey and user
        passkey = Passkey.objects.get(token=credential_id)
        user = passkey.user
        credentials = [
            AttestedCredentialData(websafe_decode(p.token)) for p in user.passkeys.all()
        ]

        # Complete authentication
        cred = server.authenticate_complete(state, credentials, data)

        # Update sign count
        passkey.sign_count = cred.sign_count
        passkey.save()

        # Log the user in
        login(request, user)
        request.session["passkey_authenticated"] = True
        return JsonResponse({"status": "OK", "message": "Login Successful"})
    except Exception as e:
        logger.error(
            f"[custom_auth_complete] An exception occurred: {e}", exc_info=True
        )
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
    origin = request.headers.get("Origin")
    logger.info(
        f"[dynamic_reg_begin] Received request. Host: '{host}', Origin header: '{origin}'"
    )

    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    logger.info(
        f"[dynamic_reg_begin] Constructed RP Entity: id='{rp_entity.id}', name='{rp_entity.name}'"
    )

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

    logger.info(
        f"[dynamic_reg_begin] Generated registration_data for client: {registration_data}"
    )
    logger.info(f"[dynamic_reg_begin] Storing state in session: {state}")
    request.session["fido2_state"] = state
    return JsonResponse(dict(registration_data))


@require_POST
@login_required
@never_cache
def dynamic_reg_complete(request):
    """Replicates the library's reg_complete logic with a dynamic FIDO server ID."""
    enable_json_mapping()
    host = request.get_host().split(":")[0]
    origin = request.headers.get("Origin")
    logger.info(
        f"[dynamic_reg_complete] Received request. Host: '{host}', Origin header: '{origin}'"
    )

    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    logger.info(
        f"[dynamic_reg_complete] Constructed RP Entity: id='{rp_entity.id}', name='{rp_entity.name}'"
    )

    server = Fido2Server(rp_entity, attestation=AttestationConveyancePreference.NONE)

    try:
        data = json.loads(request.body)
        logger.info(f"[dynamic_reg_complete] Request body data: {data}")

        state = request.session.pop("fido2_state")
        logger.info(f"[dynamic_reg_complete] Retrieved state from session: {state}")

        credential = server.register_complete(state, data)
        logger.info(
            f"[dynamic_reg_complete] Successfully completed registration with server. Credential object vars: {vars(credential)}"
        )
        logger.info(
            f"[dynamic_reg_complete] Credential data object vars: {vars(credential.credential_data)}"
        )

        logger.info("[dynamic_reg_complete] Creating and saving new Passkey object.")
        passkey = Passkey.objects.create(
            user=request.user,
            credential_id=websafe_encode(credential.credential_data.credential_id),
            token=websafe_encode(cbor2.dumps(credential.credential_data.public_key)),
            name=data.get(
                "name",
                f"Passkey-{websafe_encode(credential.credential_data.credential_id)[:8]}",
            ),
        )
        logger.info(
            f"[dynamic_reg_complete] Successfully created passkey with ID: {passkey.id} for user: {request.user.username}"
        )
        return JsonResponse({"status": "OK", "message": "Registration Successful"})
    except Exception as e:
        logger.error(
            f"[dynamic_reg_complete] An exception occurred during registration completion: {e}",
            exc_info=True,
        )
        return JsonResponse(
            {"status": "ERROR", "message": f"Registration failed: {e}"}, status=400
        )


def dynamic_auth_begin(request):
    """Replicates the library's auth_begin logic with a dynamic FIDO server ID."""
    enable_json_mapping()
    host = request.get_host().split(":")[0]
    origin = request.headers.get("Origin")
    logger.info(
        f"[dynamic_auth_begin] Received request. Host: '{host}', Origin header: '{origin}'"
    )

    rp_entity = PublicKeyCredentialRpEntity(id=host, name="Atilano Garcia's Website")
    logger.info(
        f"[dynamic_auth_begin] Constructed RP Entity: id='{rp_entity.id}', name='{rp_entity.name}'"
    )

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

    logger.info(f"[dynamic_auth_begin] Generated auth_data for client: {auth_data}")
    logger.info(f"[dynamic_auth_begin] Storing state in session: {state}")
    request.session["fido2_auth_state"] = state
    return JsonResponse(dict(auth_data))
