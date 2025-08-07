#!/usr/bin/env python
"""
Test Django passkey registration with authenticated user
"""
import json
import os
import sys

import django
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

# Setup Django
sys.path.append("/Users/tilog7/code/atilanogarciawebsite")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atilanogarciawebsite.settings")
django.setup()


def test_passkey_registration():
    print("=== Django Passkey Registration Test ===")

    # Create a test client
    client = Client()

    # Create a test user
    try:
        User.objects.get(username="testuser")
        print("✓ Using existing test user")
    except User.DoesNotExist:
        User.objects.create_user(username="testuser", password="testpass123")
        print("✓ Created new test user")

    # Log in the user
    login_success = client.login(username="testuser", password="testpass123")
    if not login_success:
        print("✗ Failed to log in test user")
        return False
    print("✓ Test user logged in successfully")

    # Test the passkey registration begin endpoint
    print("\n--- Testing passkey registration begin ---")
    try:
        url = reverse("mainwebsite:custom_passkey_reg_begin")
        print(f"Testing URL: {url}")

        response = client.post(url, content_type="application/json")
        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            print("✓ Registration begin successful")

            # Parse the JSON response
            try:
                data = response.json()
                print("✓ JSON response parsed successfully")

                # Check for required fields
                required_fields = ["challenge", "rp", "user", "pub_key_cred_params"]
                missing_fields = []

                for field in required_fields:
                    if field in data:
                        print(f"  ✓ {field}: present")
                        if field == "pub_key_cred_params":
                            print(f"    Algorithms count: {len(data[field])}")
                            for i, alg in enumerate(data[field][:3]):  # Show first 3
                                print(f"    Algorithm {i}: {alg}")
                    else:
                        missing_fields.append(field)
                        print(f"  ✗ {field}: missing")

                if missing_fields:
                    print(f"✗ Missing required fields: {missing_fields}")
                    return False
                else:
                    print("✓ All required fields present")
                    return True

            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse JSON response: {e}")
                print(f"Raw response: {response.content}")
                return False

        else:
            print(f"✗ Registration begin failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error response: {error_data}")
            except json.JSONDecodeError:
                print(f"Raw error response: {response.content}")
            return False

    except Exception as e:
        print(f"✗ Exception during registration test: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_passkey_registration()
    if success:
        print("\n=== Passkey registration test PASSED ===")
    else:
        print("\n=== Passkey registration test FAILED ===")
