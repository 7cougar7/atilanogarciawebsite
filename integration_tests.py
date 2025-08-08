"""
Integration tests for Django passkey functionality
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class PasskeyIntegrationTests(TestCase):
    """Integration tests for passkey registration and authentication flows"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

    def test_passkey_registration_begin(self):
        """Test passkey registration begin endpoint"""
        # Log in the user first (required for registration)
        self.client.login(username="testuser", password="testpass123")

        # Test the passkey registration begin endpoint
        url = reverse("mainwebsite:custom_passkey_reg_begin")
        response = self.client.post(url, content_type="application/json")

        self.assertEqual(response.status_code, 200)

        # Parse the JSON response
        data = response.json()

        # Check for required fields in the response
        required_fields = ["challenge", "rp", "user", "pub_key_cred_params"]
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")

        # Verify specific field structures
        self.assertIsInstance(data["pub_key_cred_params"], list)
        self.assertGreater(len(data["pub_key_cred_params"]), 0)

        # Verify RP information
        self.assertIn("id", data["rp"])
        self.assertIn("name", data["rp"])

        # Verify user information
        self.assertIn("id", data["user"])
        self.assertIn("name", data["user"])
        # Note: The user name might be empty in the response, which is acceptable
        self.assertIn("display_name", data["user"])
        self.assertEqual(data["user"]["display_name"], "testuser")

    def test_passkey_registration_begin_unauthenticated(self):
        """Test that unauthenticated users cannot start passkey registration"""
        url = reverse("mainwebsite:custom_passkey_reg_begin")
        response = self.client.post(url, content_type="application/json")

        # Should redirect to login (302) or return unauthorized (401/403)
        self.assertIn(response.status_code, [302, 401, 403])

    def test_passkey_auth_begin_nonexistent_user(self):
        """Test passkey auth begin with non-existent user"""
        url = reverse("mainwebsite:custom_passkey_auth_begin")
        data = {"username": "nonexistentuser"}

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        # Should return an error for non-existent user
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")

    def test_unified_login_flow_integration(self):
        """Test the unified login flow integration"""
        url = reverse("mainwebsite:login")

        # Test with existing user
        response = self.client.post(url, {"username": "testuser"})

        # Should either redirect or return success
        self.assertIn(response.status_code, [200, 302])

        if response.status_code == 200:
            # Check if it's an HTML response (which is expected for non-AJAX requests)
            self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
            # Should contain login-related content
            self.assertContains(response, "login", status_code=200)

    def test_personal_ai_protection(self):
        """Test that personal-ai page is protected"""
        url = reverse("mainwebsite:personal_ai")

        # Unauthenticated access should redirect
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Should redirect to login with next parameter
        self.assertIn("/login/", response.url)
        self.assertIn("next=%2Fpersonal-ai%2F", response.url)
