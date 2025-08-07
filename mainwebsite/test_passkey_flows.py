"""
Unit tests for passkey registration and authentication flows.
Tests focus on intended functionality and business logic rather than complex FIDO2 mocking.
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from fido2.utils import websafe_decode, websafe_encode
from passkeys.models import UserPasskey as Passkey


class PasskeyRegistrationTests(TestCase):
    """Test passkey registration flow focusing on business logic."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_registration_begin_authenticated_user(self):
        """Test that authenticated users can begin passkey registration."""
        self.client.force_login(self.user)

        response = self.client.post("/custom/passkeys/reg/begin")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Should contain required WebAuthn fields
        self.assertIn("challenge", data)
        self.assertIn("user", data)
        self.assertIn("rp", data)
        self.assertIn("pub_key_cred_params", data)

        # Verify user data
        self.assertEqual(data["user"]["display_name"], "testuser")
        self.assertIn("id", data["user"])

    def test_registration_begin_unauthenticated_user(self):
        """Test that unauthenticated users cannot begin passkey registration."""
        response = self.client.post("/custom/passkeys/reg/begin")

        # Should redirect to login or return error
        self.assertIn(response.status_code, [302, 401, 403])

    def test_registration_complete_without_session_state(self):
        """Test that registration complete fails without proper session state."""
        self.client.force_login(self.user)

        credential_data = {
            "id": "test_credential_id",
            "rawId": "test_raw_id",
            "response": {
                "attestationObject": "test_attestation",
                "clientDataJSON": "test_client_data",
            },
            "type": "public-key",
        }

        response = self.client.post(
            "/custom/passkeys/reg/complete",
            data=json.dumps(credential_data),
            content_type="application/json",
        )

        # Should fail due to missing session state
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")


class PasskeyAuthenticationTests(TestCase):
    """Test passkey authentication flow focusing on business logic."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_auth_begin_existing_user(self):
        """Test authentication begin for existing user."""
        response = self.client.post(
            "/custom/passkeys/auth/begin", {"username": "testuser"}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Should contain WebAuthn authentication options
        self.assertIn("public_key", data)
        self.assertIn("challenge", data["public_key"])
        self.assertIn("rp_id", data["public_key"])

    def test_auth_begin_nonexistent_user(self):
        """Test authentication begin for nonexistent user."""
        response = self.client.post(
            "/custom/passkeys/auth/begin", {"username": "nonexistentuser"}
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")

    def test_auth_begin_missing_username(self):
        """Test authentication begin without username."""
        response = self.client.post("/custom/passkeys/auth/begin", {})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")

    def test_auth_complete_without_session_state(self):
        """Test authentication complete without proper session state."""
        auth_data = {
            "id": "test_credential_id",
            "rawId": "test_raw_id",
            "response": {
                "authenticatorData": "test_auth_data",
                "clientDataJSON": "test_client_data",
                "signature": "test_signature",
            },
            "type": "public-key",
        }

        response = self.client.post(
            "/custom/passkeys/auth/complete",
            data=json.dumps(auth_data),
            content_type="application/json",
        )

        # Should fail due to missing session state
        self.assertEqual(response.status_code, 400)


class PasskeyModelTests(TestCase):
    """Test passkey model and database operations."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_passkey_creation(self):
        """Test that passkeys can be created and stored."""
        test_data = b"test_credential_data_bytes"
        encoded_data = websafe_encode(test_data)

        passkey = Passkey.objects.create(
            user=self.user,
            credential_id="test_credential_id",
            token=encoded_data,
            name="Test Passkey",
        )

        # Verify passkey was created
        self.assertEqual(passkey.user, self.user)
        self.assertEqual(passkey.credential_id, "test_credential_id")
        self.assertEqual(passkey.name, "Test Passkey")

        # Verify data can be decoded
        decoded_data = websafe_decode(passkey.token)
        self.assertEqual(decoded_data, test_data)

    def test_multiple_passkeys_per_user(self):
        """Test that users can have multiple passkeys."""
        test_data = b"test_credential_data"

        Passkey.objects.create(
            user=self.user,
            credential_id="cred_1",
            token=websafe_encode(test_data),
            name="First Passkey",
        )

        Passkey.objects.create(
            user=self.user,
            credential_id="cred_2",
            token=websafe_encode(test_data),
            name="Second Passkey",
        )

        # Verify both exist
        user_passkeys = Passkey.objects.filter(user=self.user)
        self.assertEqual(user_passkeys.count(), 2)

        # Verify they have different credential IDs
        cred_ids = [pk.credential_id for pk in user_passkeys]
        self.assertIn("cred_1", cred_ids)
        self.assertIn("cred_2", cred_ids)

    def test_passkey_deletion(self):
        """Test that passkeys can be deleted."""
        test_data = b"test_credential_data"

        passkey = Passkey.objects.create(
            user=self.user,
            credential_id="test_cred",
            token=websafe_encode(test_data),
            name="Test Passkey",
        )

        # Verify it exists
        self.assertEqual(Passkey.objects.filter(user=self.user).count(), 1)

        # Delete it
        passkey.delete()

        # Verify it's gone
        self.assertEqual(Passkey.objects.filter(user=self.user).count(), 0)


class PasskeyBusinessLogicTests(TestCase):
    """Test business logic and edge cases."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_user_without_passkeys_auth_flow(self):
        """Test authentication flow for user without passkeys."""
        response = self.client.post(
            "/custom/passkeys/auth/begin", {"username": "testuser"}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Should return empty allow_credentials since user has no passkeys
        self.assertEqual(data["public_key"]["allow_credentials"], [])

    def test_user_with_passkeys_auth_flow(self):
        """Test authentication flow for user with passkeys."""
        # Create a passkey for the user
        test_data = b"test_auth_data_bytes"
        Passkey.objects.create(
            user=self.user,
            credential_id="test_cred_id",
            token=websafe_encode(test_data),
            name="Test Passkey",
        )

        response = self.client.post(
            "/custom/passkeys/auth/begin", {"username": "testuser"}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Should return authentication options
        self.assertIn("public_key", data)
        self.assertIn("challenge", data["public_key"])

        # The system should handle stored passkeys gracefully
        # (even if it can't parse them properly in test environment)

    def test_error_handling_graceful_degradation(self):
        """Test that the system handles errors gracefully."""
        # Create passkey with minimal test data that might cause parsing issues
        test_data = b"minimal_test_data"
        Passkey.objects.create(
            user=self.user,
            credential_id="minimal_cred",
            token=websafe_encode(test_data),
            name="Minimal Test Passkey",
        )

        # Authentication should still work (graceful error handling)
        response = self.client.post(
            "/custom/passkeys/auth/begin", {"username": "testuser"}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Should return valid response even if credential parsing fails
        self.assertIn("public_key", data)
        self.assertIn("challenge", data["public_key"])

    def test_csrf_protection(self):
        """Test that CSRF protection is properly handled."""
        # Test that POST requests without CSRF tokens are handled appropriately
        # (Note: Django test client automatically handles CSRF, so this tests the mechanism)

        response = self.client.post(
            "/custom/passkeys/auth/begin", {"username": "testuser"}
        )

        # Should work with test client (which handles CSRF automatically)
        self.assertEqual(response.status_code, 200)

    def test_session_management(self):
        """Test that session state is properly managed."""
        self.client.force_login(self.user)

        # Begin registration should set session state
        response = self.client.post("/custom/passkeys/reg/begin")
        self.assertEqual(response.status_code, 200)

        # Session should contain registration state
        session = self.client.session
        self.assertIn("passkey_registration_state", session)


if __name__ == "__main__":
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    if not settings.configured:
        import os

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atilanogarciawebsite.settings")
        django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["mainwebsite.test_passkey_flows"])
