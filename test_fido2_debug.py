#!/usr/bin/env python
"""
Debug script to test FIDO2 registration exactly like our Django view
"""
import json
import os
import sys
from dataclasses import asdict

import django
from django.http import JsonResponse
from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestationConveyancePreference,
    PublicKeyCredentialRpEntity,
    ResidentKeyRequirement,
)

from mainwebsite.custom_passkey_views import BytesEncoder

# Setup Django
sys.path.append("/Users/tilog7/code/atilanogarciawebsite")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atilanogarciawebsite.settings")
django.setup()


def test_fido2_registration():
    print("=== FIDO2 Registration Debug Test ===")

    # Create server exactly like our view
    rp_id = "localhost"
    rp = PublicKeyCredentialRpEntity(id=rp_id, name="Atilano Garcia Website")
    server = Fido2Server(rp, attestation=AttestationConveyancePreference.NONE)
    print(f"✓ Created FIDO2 server with rp_id: {rp_id}")

    # User info exactly like our view (using a test username)
    username = "testuser"
    user_info = {
        "id": username.encode("utf-8"),
        "name": "",  # get_full_name() returns empty for test user
        "displayName": username,
    }
    print(f"✓ Created user_info: {user_info}")

    # Empty credentials list (no existing passkeys)
    user_credentials = []
    print(f"✓ User credentials: {user_credentials}")

    # Test register_begin call
    print("\n--- Testing register_begin call ---")
    try:
        registration_data, state = server.register_begin(
            user_info,
            user_credentials,
            resident_key_requirement=ResidentKeyRequirement.REQUIRED,
        )
        print("✓ register_begin call successful")
        print(f"  Registration data type: {type(registration_data)}")
        print(f"  State type: {type(state)}")
    except Exception as e:
        print(f"✗ register_begin failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test asdict conversion
    print("\n--- Testing asdict conversion ---")
    try:
        reg_dict = asdict(registration_data)
        print("✓ asdict conversion successful")
        print(f"  Dict keys: {list(reg_dict.keys())}")

        if "public_key" in reg_dict:
            pk = reg_dict["public_key"]
            print(f"  public_key keys: {list(pk.keys())}")

            # Check for pub_key_cred_params
            if "pub_key_cred_params" in pk:
                print(
                    f"  ✓ pub_key_cred_params found: {len(pk['pub_key_cred_params'])} algorithms"
                )
                for i, param in enumerate(pk["pub_key_cred_params"]):
                    print(f"    Algorithm {i}: {param}")
            else:
                print("  ✗ pub_key_cred_params missing!")
                return False
        else:
            print("  ✗ public_key missing from reg_dict!")
            return False

    except Exception as e:
        print(f"✗ asdict conversion failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test JSON serialization with BytesEncoder
    print("\n--- Testing JSON serialization ---")
    try:
        public_key_options = reg_dict.get("public_key", {})

        # Test our BytesEncoder
        response = JsonResponse(public_key_options, encoder=BytesEncoder, safe=False)
        print("✓ JsonResponse creation successful")

        # Get the actual JSON content
        json_content = response.content.decode("utf-8")
        parsed_json = json.loads(json_content)
        print("✓ JSON parsing successful")

        # Check if pub_key_cred_params is in the final JSON
        if "pub_key_cred_params" in parsed_json:
            print(
                f"  ✓ pub_key_cred_params in final JSON: {len(parsed_json['pub_key_cred_params'])} algorithms"
            )
            for i, param in enumerate(parsed_json["pub_key_cred_params"]):
                print(f"    Final algorithm {i}: {param}")
        else:
            print("  ✗ pub_key_cred_params missing from final JSON!")
            return False

    except Exception as e:
        print(f"✗ JSON serialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n=== All tests passed! ===")
    return True


if __name__ == "__main__":
    success = test_fido2_registration()
    if success:
        print("\nThe FIDO2 registration should work. The issue might be elsewhere.")
    else:
        print("\nFound the issue in FIDO2 registration!")
