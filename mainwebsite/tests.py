import json
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

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
    def test_dynamic_reg_begin_authenticated(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.register_begin.return_value = ({}, "state")

        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("mainwebsite:custom_passkey_reg_begin"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("passkey_registration_state", self.client.session)
        mock_server.register_begin.assert_called_once()

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_complete_success(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_credential = MagicMock()
        mock_credential.credential_data = b"credential_data"
        mock_server.register_complete.return_value = mock_credential

        self.client.login(username="testuser", password="password")
        session = self.client.session
        session["passkey_registration_state"] = "state"
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
        self.assertEqual(response.json(), {"status": "OK"})
        self.assertTrue(UserPasskey.objects.filter(user=self.user).exists())

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_reg_complete_failure(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.register_complete.side_effect = Exception("Test Error")

        self.client.login(username="testuser", password="password")
        session = self.client.session
        session["passkey_registration_state"] = "state"
        session.save()

        response = self.client.post(
            reverse("mainwebsite:custom_passkey_reg_complete"),
            data=json.dumps(self.passkey_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_dynamic_auth_begin(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.authenticate_begin.return_value = ({}, "state")

        response = self.client.get(reverse("mainwebsite:custom_passkey_auth_begin"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("passkey_authentication_state", self.client.session)
        mock_server.authenticate_begin.assert_called_once()

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_custom_auth_complete_success(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.authenticate_complete.return_value = None  # Success

        UserPasskey.objects.create(
            user=self.user,
            credential_id=self.passkey_data["id"],
            token="some_token",
            name="test_passkey",
        )

        session = self.client.session
        session["passkey_authentication_state"] = "state"
        session.save()

        with patch(
            "mainwebsite.custom_passkey_views.websafe_decode",
            return_value=b"decoded_token",
        ), patch(
            "mainwebsite.custom_passkey_views.AttestedCredentialData"
        ) as mock_attested_credential:
            # The view iterates over this, so it needs to be iterable.
            mock_attested_credential.return_value = [MagicMock()]
            response = self.client.post(
                reverse("mainwebsite:custom_passkey_auth_complete"),
                data=json.dumps(self.passkey_data),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")
        self.assertTrue(response.json()["debug"]["user_authenticated"])

    @patch("mainwebsite.custom_passkey_views.get_fido2_server")
    def test_custom_auth_complete_failure(self, mock_get_fido2_server):
        mock_server = MagicMock()
        mock_get_fido2_server.return_value = mock_server
        mock_server.authenticate_complete.side_effect = Exception("Auth Failed")

        UserPasskey.objects.create(
            user=self.user,
            credential_id=self.passkey_data["id"],
            token="some_token",
            name="test_passkey",
        )

        session = self.client.session
        session["passkey_authentication_state"] = "state"
        session.save()

        with patch(
            "mainwebsite.custom_passkey_views.websafe_decode",
            return_value=b"decoded_token",
        ), patch(
            "mainwebsite.custom_passkey_views.AttestedCredentialData",
            return_value=MagicMock(),
        ):
            response = self.client.post(
                reverse("mainwebsite:custom_passkey_auth_complete"),
                data=json.dumps(self.passkey_data),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
