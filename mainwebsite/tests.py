import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from passkeys.models import UserPasskey


class PasskeyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="password", email="test@example.com"
        )
        self.passkey_data = {
            "id": "test_credential_id",
            "rawId": "test_credential_id",
            "response": {"clientDataJSON": "{}", "attestationObject": "{}"},
            "type": "public-key",
        }

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_begin_unauthenticated(self, mock_get_fido2_server):
        response = self.client.get(reverse("mainwebsite:custom_passkey_reg_begin"))
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("login_url", data)
        self.assertIn(reverse("mainwebsite:login"), data["login_url"])

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_begin_returns_flat_json(self, mock_get_fido2_server):
        # 1. Setup
        self.client.login(username="testuser", password="password")
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server

        # 2. Mock the data returned by fido2_server.register_begin
        # This mimics the structure that `asdict` will convert
        mock_public_key_options_dict = {
            "challenge": b"some_challenge_bytes",
            "rp": {"id": "localhost", "name": "Test RP"},
            "user": {
                "id": b"user_id_bytes",
                "name": "testuser",
                "displayName": "testuser",
            },
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        }
        # The view's logging expects an object with attributes, not a dict.
        mock_registration_data = MagicMock()
        mock_registration_data.public_key.challenge = b"some_challenge_bytes"
        mock_registration_data.public_key.user.id = b"user_id_bytes"

        # The view uses `asdict`, so we mock it to return the dict version of our mock object
        with patch(
            "mainwebsite.custom_passkey_views.asdict",
            return_value={"public_key": mock_public_key_options_dict},
        ):
            mock_server.register_begin.return_value = (
                mock_registration_data,
                "dummy_state",
            )

            # 3. Make the request
            response = self.client.post(reverse("mainwebsite:custom_passkey_reg_begin"))

        # 4. Assertions
        self.assertEqual(response.status_code, 200)

        # The custom BytesEncoder will have encoded the bytes to strings
        response_data = response.json()

        # Check that the response is the flat public_key object, not nested
        self.assertIn("challenge", response_data)
        self.assertIn("rp", response_data)
        self.assertIn("user", response_data)
        self.assertEqual(response_data["rp"]["id"], "localhost")
        # The key should not be 'public_key'
        self.assertNotIn("public_key", response_data)

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_begin_authenticated(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        # Mock a dataclass-like object for the return value
        mock_registration_data = MagicMock()
        # Set the attributes that the logging in the view will access
        mock_registration_data.public_key.challenge = b""
        mock_registration_data.public_key.user.id = b""
        mock_server.register_begin.return_value = (mock_registration_data, "state")

        self.client.login(username="testuser", password="password")
        # The view uses `asdict`, so we mock it to return a dict from our mock object
        with patch(
            "mainwebsite.custom_passkey_views.asdict", return_value={"public_key": {}}
        ):
            response = self.client.post(reverse("mainwebsite:custom_passkey_reg_begin"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("passkey_registration_state", self.client.session)
        mock_server.register_begin.assert_called_once()

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_complete_success(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_credential = MagicMock()
        mock_credential.credential_id = b"credential_id"  # Corrected attribute
        mock_server.register_complete.return_value = mock_credential

        self.client.login(username="testuser", password="password")
        session = self.client.session
        session["passkey_registration_state"] = "dummy_state"
        session.save()

        with patch(
            "mainwebsite.custom_passkey_views.websafe_encode",
            return_value="encoded_token",
        ):
            response = self.client.post(
                reverse("mainwebsite:custom_passkey_reg_complete"),
                data=json.dumps(self.passkey_data),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_complete_failure(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.register_complete.side_effect = Exception("Test Error")

        self.client.login(username="testuser", password="password")
        session = self.client.session
        session["passkey_registration_state"] = "dummy_state"
        session.save()

        response = self.client.post(
            reverse("mainwebsite:custom_passkey_reg_complete"),
            data=json.dumps({"name": "test_passkey"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["status"], "error")

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_auth_begin(self, mock_get_fido2_server):
        session = self.client.session
        session["webauthn_username"] = self.user.username
        session.save()

        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        # Mock a dataclass-like object
        mock_auth_data = MagicMock()
        mock_server.authenticate_begin.return_value = (mock_auth_data, "state")

        with patch("mainwebsite.custom_passkey_views.asdict", return_value={}):
            response = self.client.post(
                reverse("mainwebsite:custom_passkey_auth_begin")
            )
        self.assertEqual(response.status_code, 200)

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_custom_auth_complete_failure(self, mock_get_fido2_server):
        self.client.login(username="testuser", password="password")
        session = self.client.session
        session["passkey_auth_state"] = "dummy_state"
        session["webauthn_username"] = self.user.username
        session.save()

        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.authenticate_complete.side_effect = Exception("Test Error")

        response = self.client.post(
            reverse("mainwebsite:custom_passkey_auth_complete"),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_redirect_after_passkey_registration(self, mock_get_fido2_server):
        # 1. Simulate the initial login request with a 'next' parameter
        next_page = "/personal_ai/"
        session = self.client.session
        session["next"] = next_page
        session.save()

        # 2. Simulate the magic link verification to log the user in
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.client.get(
            reverse(
                "mainwebsite:magic_link_verify", kwargs={"uidb64": uid, "token": token}
            )
        )

        # 3. Set the session state required for registration completion
        session = self.client.session
        session["passkey_registration_state"] = "dummy_state"
        session["login_next_url"] = (
            next_page  # Set the next url for the registration view
        )
        session.save()

        # 4. Mock the passkey registration completion
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_credential = MagicMock()
        mock_credential.credential_id = b"credential_id"  # Corrected attribute
        mock_server.register_complete.return_value = mock_credential

        with patch(
            "mainwebsite.custom_passkey_views.websafe_encode",
            return_value="encoded_token",
        ):
            response = self.client.post(
                reverse("mainwebsite:custom_passkey_reg_complete"),
                data=json.dumps(self.passkey_data),
                content_type="application/json",
            )

        # 5. Check that the response contains the correct redirect URL
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")
        self.assertEqual(response.json()["redirect_url"], next_page)


class UnifiedLoginFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="password", email="test@example.com"
        )

    def test_unified_login_page_loads(self):
        response = self.client.get(reverse("mainwebsite:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "unified_login.html")

    def test_unified_login_nonexistent_user(self):
        response = self.client.post(
            reverse("mainwebsite:login"), {"username": "nouser"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No account found with that username.")

    def test_unified_login_with_nonexistent_user_ajax(self):
        response = self.client.post(
            reverse("mainwebsite:login"),
            {"username": "nouser"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["action"], "error")

    @patch("mainwebsite.views.UnifiedLoginView.send_magic_link")
    def test_unified_login_sends_magic_link_for_user_without_passkey(
        self, mock_send_magic_link
    ):
        response = self.client.post(
            reverse("mainwebsite:login"), {"username": "testuser"}
        )
        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Please check your email for a magic link to register your first passkey.",
        )
        mock_send_magic_link.assert_called_once()

    @patch("mainwebsite.views.UnifiedLoginView.send_magic_link")
    def test_unified_login_sends_magic_link_for_user_without_passkey_ajax(
        self, mock_send_magic_link
    ):
        response = self.client.post(
            reverse("mainwebsite:login"),
            {"username": "testuser"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "magic_link_sent")
        mock_send_magic_link.assert_called_once()

    def test_unified_login_prompts_for_passkey_ajax(self):
        UserPasskey.objects.create(
            user=self.user, token="some_token", credential_id="some_id"
        )
        response = self.client.post(
            reverse("mainwebsite:login"),
            {"username": "testuser"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "prompt_passkey")

    def test_unified_login_redirects_user_with_passkey(self):
        UserPasskey.objects.create(
            user=self.user, token="some_token", credential_id="some_id"
        )
        response = self.client.post(
            reverse("mainwebsite:login"), {"username": "testuser"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("mainwebsite:passkey_login"), response.url)

    def test_magic_link_verify_success(self):
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse(
                "mainwebsite:magic_link_verify", kwargs={"uidb64": uid, "token": token}
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("mainwebsite:passkey_register"))
        # Check that the user is logged in
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_magic_link_verify_failure(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse(
                "mainwebsite:magic_link_verify",
                kwargs={"uidb64": uid, "token": "invalid-token"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "magic_link_invalid.html")
