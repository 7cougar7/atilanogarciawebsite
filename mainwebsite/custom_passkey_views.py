import json
import logging
from dataclasses import asdict

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from fido2.server import Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import (
    AttestationConveyancePreference,
    AuthenticatorData,
    PublicKeyCredentialRpEntity,
    ResidentKeyRequirement,
)
from passkeys.models import UserPasskey as Passkey

from mainwebsite.error_handling import (
    handle_view_exception,
    log_security_event,
    secure_json_error_response,
)

logger = logging.getLogger(__name__)


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return websafe_encode(obj)
        return super().default(obj)


def get_fido2_server(request):
    rp_id = request.get_host().split(":")[0]
    logger.info(f"get_fido2_server: Creating FIDO2 server with rp_id: {rp_id}")
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
    try:
        if not request.user.is_authenticated:
            log_security_event(
                "unauthenticated_passkey_registration_attempt",
                {"path": request.path},
                request=request,
            )
            login_url = f"{reverse('mainwebsite:login')}?next={reverse('mainwebsite:passkey_register')}"
            return JsonResponse(
                {
                    "error": "You must be logged in to register a new passkey.",
                    "redirect_url": login_url,
                },
                status=401,
            )

        user = request.user
        logger.info(f"dynamic_reg_begin: User: {user.username} (ID: {user.id})")

        existing_credentials = get_user_credentials(user)
        logger.info(
            f"dynamic_reg_begin: Found {len(existing_credentials)} existing credentials"
        )

        fido2_server = get_fido2_server(request)

        user_info = {
            "id": user.username.encode("utf-8"),
            "name": user.get_full_name() or "",
            "displayName": user.username,
        }

        try:
            logger.info("dynamic_reg_begin: Calling fido2_server.register_begin")
            registration_data, state = fido2_server.register_begin(
                user_info,
                existing_credentials,
                resident_key_requirement=ResidentKeyRequirement.PREFERRED,
            )
            logger.info("dynamic_reg_begin: register_begin call successful")

            request.session["passkey_registration_state"] = state
            logger.info("dynamic_reg_begin: Registration state saved to session")

            public_key_options = asdict(registration_data)["public_key"]
            return JsonResponse(public_key_options, encoder=BytesEncoder, safe=False)

        except Exception as e:
            handle_view_exception(e, request, user, "dynamic_reg_begin_asdict")
            logger.error(f"dynamic_reg_begin: Error in asdict conversion: {e}")
            return secure_json_error_response("passkey_error", 500)

    except Exception as e:
        handle_view_exception(e, request, user, "dynamic_reg_begin_general")
        return secure_json_error_response("server_error", 500)


@require_POST
@login_required
def dynamic_reg_complete(request):
    try:
        fido2_server = get_fido2_server(request)
        data = json.loads(request.body)
        state = request.session.get("passkey_registration_state")

        if not state:
            log_security_event("Registration state not found in session")
            return secure_json_error_response("Invalid request")

        credential = fido2_server.register_complete(state, data)

        credential_id = data.get("id")
        if not credential_id:
            log_security_event("Credential ID not found in request data")
            return secure_json_error_response("Invalid request")

        encoded_credential = websafe_encode(credential)

        Passkey.objects.create(
            user=request.user,
            token=encoded_credential,
            credential_id=credential_id,
            name=data.get("name", f"Passkey {timezone.now():%Y-%m-%d}"),
        )

        del request.session["passkey_registration_state"]

        login_url = reverse("mainwebsite:login")
        return JsonResponse({"status": "OK", "redirect_url": login_url})

    except Exception as e:
        handle_view_exception(e, request, "dynamic_reg_complete")
        return secure_json_error_response("Registration failed")


def dynamic_auth_begin(request):
    logger.info(f"dynamic_auth_begin: POST data: {request.POST}")
    fido2_server = get_fido2_server(request)
    username = request.POST.get("username")
    logger.info(f"dynamic_auth_begin: username from POST: {username}")
    if not username:
        log_security_event(
            "missing_username_in_auth_begin", {"path": request.path}, request=request
        )
        return JsonResponse(
            {"status": "error", "message": "Username not provided."}, status=400
        )

    try:
        user = User.objects.get(username=username)
        logger.info(f"dynamic_auth_begin: Found user: {username}")
    except User.DoesNotExist:
        log_security_event(
            "user_not_found_in_auth_begin", {"username": username}, request=request
        )
        return JsonResponse(
            {"status": "error", "message": "User not found."}, status=404
        )

    keys = Passkey.objects.filter(user=user)
    logger.info(f"dynamic_auth_begin: Found {len(keys)} credentials for user.")

    credentials = []
    for k in keys:
        try:
            auth_data = AuthenticatorData(websafe_decode(k.token))

            if auth_data.is_attested():
                attested_cred_data = auth_data.credential_data
                credentials.append(attested_cred_data)
                logger.info(
                    f"dynamic_auth_begin: added AttestedCredentialData for {k.credential_id}"
                )
            else:
                logger.warning(
                    f"dynamic_auth_begin: Stored credential {k.credential_id} is not attested"
                )
        except Exception as e:
            handle_view_exception(
                e, request, user, "dynamic_auth_begin_credential_processing"
            )
            logger.error(
                f"dynamic_auth_begin: Error processing credential {k.credential_id}: {e}"
            )
            continue

    logger.info(
        f"dynamic_auth_begin: Successfully processed {len(credentials)} credentials."
    )

    auth_data, state = fido2_server.authenticate_begin(credentials)
    logger.info(f"dynamic_auth_begin: auth_data generated: {auth_data}")
    request.session["passkey_auth_state"] = state
    logger.info("dynamic_auth_begin: passkey_auth_state saved to session.")

    return JsonResponse(asdict(auth_data), encoder=BytesEncoder, safe=False)


@require_POST
def custom_auth_complete(request):
    logger.debug(f"custom_auth_complete: request body: {request.body}")
    logger.debug(f"custom_auth_complete: session data: {request.session.items()}")
    username = None  # Initialize username to avoid UnboundLocalError
    try:
        data = json.loads(request.body)
        server = get_fido2_server(request)
        state = request.session.pop("passkey_auth_state")
        username = request.session.get("webauthn_username")

        keys = Passkey.objects.filter(user__username=username)
        logger.debug(f"custom_auth_complete: found {keys.count()} keys for user")

        credentials = []
        for k in keys:
            try:
                auth_data = AuthenticatorData(websafe_decode(k.token))

                if auth_data.is_attested():
                    attested_cred_data = auth_data.credential_data
                    credentials.append(attested_cred_data)
                    logger.debug(
                        f"custom_auth_complete: added AttestedCredentialData for {k.credential_id}"
                    )
                else:
                    logger.warning(
                        f"custom_auth_complete: Stored credential {k.credential_id} is not attested"
                    )
            except Exception as e:
                handle_view_exception(
                    e, request, username, "custom_auth_complete_credential_processing"
                )
                logger.error(
                    f"custom_auth_complete: Failed to process credential {k.credential_id}: {e}"
                )
                continue

        cred = server.authenticate_complete(
            state,
            credentials,
            data,
        )

        key = Passkey.objects.get(credential_id=websafe_encode(cred.credential_id))
        user = key.user
        login(request, user)
        request.session["passkey_authenticated"] = True
        import time

        request.session["passkey_last_activity"] = time.time()
        next_url = request.session.pop("next", "/")
        logger.debug(
            f"custom_auth_complete: login successful for user {user.username}, redirecting to {next_url}"
        )
        return JsonResponse({"status": "OK", "redirect_url": next_url})

    except Exception as e:
        handle_view_exception(e, request, username, "custom_auth_complete_general")
        return secure_json_error_response("authentication_failed", 400)
