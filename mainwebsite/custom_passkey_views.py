import json
import logging
from dataclasses import asdict

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
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


@csrf_exempt
def dynamic_reg_begin(request):
    if not request.user.is_authenticated:
        logger.error("dynamic_reg_begin: User not authenticated")
        login_url = f"{reverse('mainwebsite:login')}?next={reverse('mainwebsite:passkey_register')}"
        return JsonResponse(
            {
                "error": "You must be logged in to register a new passkey.",
                "redirect_url": login_url,
            },
            status=401,
        )

    try:
        user = request.user
        logger.info(f"dynamic_reg_begin: User: {user.username} (ID: {user.id})")

        # Get existing credentials for this user
        existing_credentials = get_user_credentials(user)
        logger.info(
            f"dynamic_reg_begin: Found {len(existing_credentials)} existing credentials"
        )

        # Get FIDO2 server instance
        fido2_server = get_fido2_server(request)

        # Create user info for FIDO2
        user_info = {
            "id": user.username.encode("utf-8"),
            "name": user.get_full_name() or "",
            "displayName": user.username,
        }

        # Begin registration
        try:
            logger.info("dynamic_reg_begin: Calling fido2_server.register_begin")
            registration_data, state = fido2_server.register_begin(
                user_info,
                existing_credentials,
                resident_key_requirement=ResidentKeyRequirement.REQUIRED,
            )
            logger.info("dynamic_reg_begin: register_begin call successful")

            # Store state in session
            request.session["passkey_registration_state"] = state
            logger.info("dynamic_reg_begin: Registration state saved to session")

            # Convert to dictionary for JSON serialization
            public_key_options = asdict(registration_data)["public_key"]
            return JsonResponse(public_key_options, encoder=BytesEncoder, safe=False)

        except Exception as e:
            logger.error(f"dynamic_reg_begin: Error in asdict conversion: {e}")
            raise

    except Exception as e:
        logger.error(f"dynamic_reg_begin: General error: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_POST
@login_required
def dynamic_reg_complete(request):
    try:
        fido2_server = get_fido2_server(request)
        data = json.loads(request.body)
        state = request.session.get("passkey_registration_state")

        if not state:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Registration state not found in session.",
                },
                status=400,
            )

        # Verify the credential with the FIDO2 server
        credential = fido2_server.register_complete(state, data)

        # Extract credential ID from the request data (not from the AuthenticatorData object)
        credential_id = data.get("id")  # This is the credential ID from the browser
        if not credential_id:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Credential ID not found in request data.",
                },
                status=400,
            )

        # The credential object is AuthenticatorData, we need to encode it for storage
        encoded_credential = websafe_encode(credential)

        Passkey.objects.create(
            user=request.user,
            token=encoded_credential,
            credential_id=credential_id,  # Use the ID from the request data
            name=data.get("name", f"Passkey {timezone.now():%Y-%m-%d}"),
        )

        # Clear the registration state from the session
        del request.session["passkey_registration_state"]

        # After successful passkey registration, redirect to login page to complete authentication
        login_url = reverse("mainwebsite:login")

        return JsonResponse({"status": "OK", "redirect_url": login_url})

    except Exception as e:
        logger.error(f"Error in custom_passkey_reg_complete: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def dynamic_auth_begin(request):
    logger.info(f"dynamic_auth_begin: POST data: {request.POST}")
    fido2_server = get_fido2_server(request)
    username = request.POST.get("username")
    logger.info(f"dynamic_auth_begin: username from POST: {username}")
    if not username:
        username = request.session.get("webauthn_username")
        logger.info(f"dynamic_auth_begin: username from session: {username}")

    if not username:
        logger.error("dynamic_auth_begin: Username not found in POST or session.")
        return JsonResponse(
            {"status": "error", "message": "Username not provided."}, status=400
        )

    try:
        user = User.objects.get(username=username)
        logger.info(f"dynamic_auth_begin: Found user: {user}")
    except User.DoesNotExist:
        logger.error(f"dynamic_auth_begin: User '{username}' not found.")
        return JsonResponse(
            {"status": "error", "message": "User not found."}, status=404
        )

    keys = Passkey.objects.filter(user=user)
    logger.info(f"dynamic_auth_begin: Found {len(keys)} credentials for user.")

    # Extract AttestedCredentialData objects from stored AuthenticatorData
    credentials = []
    for k in keys:
        try:
            # The stored token is an encoded AuthenticatorData object
            auth_data = AuthenticatorData(websafe_decode(k.token))

            # Check if this AuthenticatorData contains attested credential data
            if auth_data.is_attested():
                # Extract the AttestedCredentialData from the AuthenticatorData
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

    # Convert to dictionary for JSON serialization
    return JsonResponse(asdict(auth_data), encoder=BytesEncoder, safe=False)


@require_POST
@csrf_exempt
def custom_auth_complete(request):
    logger.debug(f"custom_auth_complete: request body: {request.body}")
    logger.debug(f"custom_auth_complete: session data: {request.session.items()}")
    try:
        data = json.loads(request.body)
        server = get_fido2_server(request)
        state = request.session.pop("passkey_auth_state")
        username = request.session.get("webauthn_username")

        keys = Passkey.objects.filter(user__username=username)
        logger.debug(f"custom_auth_complete: found {keys.count()} keys for user")

        # Create AttestedCredentialData objects for authentication
        # The authenticate_complete method expects the same credential objects that were passed to authenticate_begin
        credentials = []
        for k in keys:
            try:
                # Decode the stored AuthenticatorData
                auth_data = AuthenticatorData(websafe_decode(k.token))

                # Check if this AuthenticatorData contains attested credential data
                if auth_data.is_attested():
                    # Extract the AttestedCredentialData from the AuthenticatorData
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
                logger.error(
                    f"custom_auth_complete: Failed to process credential {k.credential_id}: {e}"
                )
                continue

        cred = server.authenticate_complete(
            state,
            credentials,
            data,
        )

        # Find the passkey that was used for authentication
        # The cred object should contain the credential_id that was used
        key = Passkey.objects.get(credential_id=websafe_encode(cred.credential_id))
        user = key.user
        login(request, user)
        # Set passkey authentication flag in session
        request.session["passkey_authenticated"] = True
        next_url = request.session.pop("next", "/")
        logger.debug(
            f"custom_auth_complete: login successful for user {user.username}, redirecting to {next_url}"
        )
        return JsonResponse({"status": "OK", "redirect_url": next_url})

    except Exception as e:
        logger.error(f"Error in custom_auth_complete: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": "Login failed"}, status=400)
