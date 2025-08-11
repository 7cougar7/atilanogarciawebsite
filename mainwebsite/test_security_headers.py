"""
Tests for security headers, CORS, and account lockout functionality.
"""

import time

from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from .account_lockout import (
    AccountLockoutManager,
    clear_login_attempts,
    is_account_locked,
    record_failed_login,
)
from .security_middleware import CORSMiddleware, SecurityHeadersMiddleware


class SecurityHeadersTests(TestCase):
    """Test security headers middleware."""

    def setUp(self):
        self.factory = RequestFactory()

        # Create a dummy get_response function for middleware testing
        def get_response(request):
            return HttpResponse()

        self.middleware = SecurityHeadersMiddleware(get_response)

    def test_security_headers_added(self):
        """Test that all security headers are added to responses."""
        request = self.factory.get("/")
        response = HttpResponse()

        # Process response through middleware
        response = self.middleware.process_response(request, response)

        # Check Content Security Policy
        self.assertIn("Content-Security-Policy", response)
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

        # Check other security headers
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")

        # Check Cross-Origin policies
        self.assertIn("Cross-Origin-Embedder-Policy", response)
        self.assertIn("Cross-Origin-Opener-Policy", response)

        # Check Permissions Policy
        self.assertIn("Permissions-Policy", response)
        permissions = response["Permissions-Policy"]
        self.assertIn("geolocation=()", permissions)
        self.assertIn("microphone=()", permissions)

    def test_server_header_removed(self):
        """Test that server information is removed from responses."""
        request = self.factory.get("/")
        response = HttpResponse()
        response["Server"] = "Apache/2.4.41"

        # Process response through middleware
        response = self.middleware.process_response(request, response)

        # Server header should be removed
        self.assertNotIn("Server", response)

    def test_csp_allows_webauthn_requirements(self):
        """Test that CSP allows necessary resources for WebAuthn."""
        request = self.factory.get("/")
        response = HttpResponse()

        # Process response through middleware
        response = self.middleware.process_response(request, response)

        csp = response["Content-Security-Policy"]
        # Should allow self for scripts and connections (needed for WebAuthn)
        self.assertIn("script-src 'self'", csp)
        self.assertIn("connect-src 'self'", csp)


class CORSMiddlewareTests(TestCase):
    """Test CORS middleware for WebAuthn endpoints."""

    def setUp(self):
        self.factory = RequestFactory()

        # Create a dummy get_response function for middleware testing
        def get_response(request):
            return HttpResponse()

        self.middleware = CORSMiddleware(get_response)

    def test_cors_headers_for_webauthn_endpoints(self):
        """Test CORS headers are added to WebAuthn endpoints."""
        webauthn_paths = [
            "/custom/passkeys/auth/begin",
            "/custom/passkeys/auth/complete",
            "/custom/passkeys/reg/begin",
            "/custom/passkeys/reg/complete",
        ]

        for path in webauthn_paths:
            with self.subTest(path=path):
                request = self.factory.post(
                    path, HTTP_ORIGIN="https://atilanogarcia.com"
                )
                response = HttpResponse()

                # Process response through middleware
                response = self.middleware.process_response(request, response)

                # Check CORS headers
                self.assertEqual(
                    response["Access-Control-Allow-Origin"], "https://atilanogarcia.com"
                )
                self.assertIn("POST", response["Access-Control-Allow-Methods"])
                self.assertIn("X-CSRFToken", response["Access-Control-Allow-Headers"])
                self.assertEqual(response["Access-Control-Allow-Credentials"], "true")

    def test_cors_preflight_options_request(self):
        """Test CORS preflight OPTIONS requests are handled."""
        request = self.factory.options(
            "/custom/passkeys/auth/begin", HTTP_ORIGIN="https://atilanogarcia.com"
        )

        # Process request through middleware
        response = self.middleware.process_request(request)

        # Should return a response for OPTIONS
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "https://atilanogarcia.com"
        )

    @override_settings(DEBUG=True)
    def test_cors_localhost_in_debug(self):
        """Test CORS allows localhost in DEBUG mode."""
        request = self.factory.post(
            "/custom/passkeys/auth/begin", HTTP_ORIGIN="http://localhost:8000"
        )
        response = HttpResponse()

        # Process response through middleware
        response = self.middleware.process_response(request, response)

        # Should allow localhost in DEBUG mode
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "http://localhost:8000"
        )

    @override_settings(DEBUG=False)
    def test_cors_blocks_unauthorized_origins(self):
        """Test CORS blocks unauthorized origins in production."""
        request = self.factory.post(
            "/custom/passkeys/auth/begin", HTTP_ORIGIN="https://malicious-site.com"
        )
        response = HttpResponse()

        # Process response through middleware
        response = self.middleware.process_response(request, response)

        # Should not set Access-Control-Allow-Origin for unauthorized origin
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_cors_not_applied_to_non_webauthn_endpoints(self):
        """Test CORS headers are not added to non-WebAuthn endpoints."""
        request = self.factory.get("/", HTTP_ORIGIN="https://atilanogarcia.com")
        response = HttpResponse()

        # Process response through middleware
        response = self.middleware.process_response(request, response)

        # Should not have CORS headers
        self.assertNotIn("Access-Control-Allow-Origin", response)


class AccountLockoutTests(TestCase):
    """Test account lockout functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        # Clear cache after each test
        cache.clear()

    @override_settings(
        ACCOUNT_LOCKOUT_MAX_ATTEMPTS=3,
        ACCOUNT_LOCKOUT_DURATION=300,
        ACCOUNT_LOCKOUT_ATTEMPT_WINDOW=60,
    )
    def test_user_lockout_after_max_attempts(self):
        """Test user gets locked after maximum failed attempts."""
        username = "testuser"
        ip_address = "127.0.0.1"

        # Record failed attempts (below threshold)
        for i in range(2):
            result = record_failed_login(username=username, ip_address=ip_address)
            self.assertFalse(result["user_locked"])
            self.assertEqual(result["user_attempts"], i + 1)

        # Third attempt should trigger lockout
        result = record_failed_login(username=username, ip_address=ip_address)
        self.assertTrue(result["user_locked"])
        self.assertEqual(result["user_attempts"], 3)
        self.assertIsNotNone(result["lockout_expires"])

        # Verify account is locked
        self.assertTrue(is_account_locked(username=username))

    @override_settings(
        ACCOUNT_LOCKOUT_MAX_ATTEMPTS=3,
        ACCOUNT_LOCKOUT_DURATION=300,
        ACCOUNT_LOCKOUT_ATTEMPT_WINDOW=60,
    )
    def test_ip_lockout_after_max_attempts(self):
        """Test IP gets locked after maximum failed attempts."""
        ip_address = "192.168.1.100"
        max_ip_attempts = 3 * 3  # IP threshold is 3x user threshold

        # Record failed attempts for different users from same IP
        for i in range(max_ip_attempts - 1):
            username = f"user{i}"
            result = record_failed_login(username=username, ip_address=ip_address)
            self.assertFalse(result["ip_locked"])

        # Final attempt should trigger IP lockout
        result = record_failed_login(username="final_user", ip_address=ip_address)
        self.assertTrue(result["ip_locked"])

        # Verify IP is locked
        self.assertTrue(is_account_locked(ip_address=ip_address))

    @override_settings(
        ACCOUNT_LOCKOUT_MAX_ATTEMPTS=3,
        ACCOUNT_LOCKOUT_DURATION=1,  # 1 second for quick test
        ACCOUNT_LOCKOUT_ATTEMPT_WINDOW=60,
    )
    def test_lockout_expires_automatically(self):
        """Test that lockout expires after the specified duration."""
        username = "testuser"

        # Trigger lockout
        for i in range(3):
            record_failed_login(username=username)

        # Verify locked
        self.assertTrue(is_account_locked(username=username))

        # Wait for lockout to expire
        time.sleep(1.1)

        # Verify no longer locked
        self.assertFalse(is_account_locked(username=username))

    def test_clear_attempts_after_successful_login(self):
        """Test clearing attempts after successful login."""
        username = "testuser"
        ip_address = "127.0.0.1"

        # Record some failed attempts
        record_failed_login(username=username, ip_address=ip_address)
        record_failed_login(username=username, ip_address=ip_address)

        # Verify attempts are recorded
        status = AccountLockoutManager.get_lockout_status(
            username=username, ip_address=ip_address
        )
        self.assertEqual(status["user_attempts"], 2)
        self.assertEqual(status["ip_attempts"], 2)

        # Clear attempts (simulate successful login)
        clear_login_attempts(username=username, ip_address=ip_address)

        # Verify attempts are cleared
        status = AccountLockoutManager.get_lockout_status(
            username=username, ip_address=ip_address
        )
        self.assertEqual(status["user_attempts"], 0)
        self.assertEqual(status["ip_attempts"], 0)

    def test_manual_unlock_account(self):
        """Test manually unlocking an account."""
        username = "testuser"

        # Trigger lockout
        for i in range(5):  # Use default max attempts
            record_failed_login(username=username)

        # Verify locked
        self.assertTrue(is_account_locked(username=username))

        # Manually unlock
        AccountLockoutManager.unlock_account(username=username)

        # Verify unlocked
        self.assertFalse(is_account_locked(username=username))

    @override_settings(
        ACCOUNT_LOCKOUT_MAX_ATTEMPTS=3,
        ACCOUNT_LOCKOUT_ATTEMPT_WINDOW=2,  # 2 seconds window
    )
    def test_old_attempts_expire(self):
        """Test that old attempts outside the window don't count."""
        username = "testuser"

        # Record 2 attempts
        record_failed_login(username=username)
        record_failed_login(username=username)

        # Wait for attempts to expire
        time.sleep(2.1)

        # Record another attempt - should not trigger lockout
        result = record_failed_login(username=username)
        self.assertFalse(result["user_locked"])
        self.assertEqual(result["user_attempts"], 1)  # Only the recent attempt counts

    def test_lockout_status_details(self):
        """Test detailed lockout status information."""
        username = "testuser"
        ip_address = "127.0.0.1"

        # Record some attempts
        record_failed_login(username=username, ip_address=ip_address)
        record_failed_login(username=username, ip_address=ip_address)

        # Get detailed status
        status = AccountLockoutManager.get_lockout_status(
            username=username, ip_address=ip_address
        )

        self.assertEqual(status["user_attempts"], 2)
        self.assertEqual(status["ip_attempts"], 2)
        self.assertFalse(status["user_locked"])
        self.assertFalse(status["ip_locked"])
        self.assertEqual(status["time_remaining"], 0)

    def test_request_object_ip_extraction(self):
        """Test extracting IP address from request object."""
        request = self.factory.post("/login/", REMOTE_ADDR="192.168.1.50")

        # Record attempt using request object
        result = record_failed_login(username="testuser", request=request)

        # Should have recorded IP attempt
        self.assertEqual(result["ip_attempts"], 1)

        # Verify lockout check works with request object
        locked = is_account_locked(username="testuser", request=request)
        self.assertFalse(locked)  # Not locked yet


class SecurityIntegrationTests(TestCase):
    """Integration tests for security features."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_security_headers_on_login_page(self):
        """Test security headers are applied to login page."""
        response = self.client.get("/login/")

        # Should have security headers
        self.assertIn("Content-Security-Policy", response)
        self.assertIn("X-Content-Type-Options", response)
        self.assertIn("X-Frame-Options", response)

    @override_settings(ACCOUNT_LOCKOUT_MAX_ATTEMPTS=2, ACCOUNT_LOCKOUT_DURATION=300)
    def test_login_with_account_lockout(self):
        """Test login behavior with account lockout enabled."""
        # Make failed login attempts by trying to log in with wrong password
        # This should trigger the User.DoesNotExist path which records failed attempts
        for i in range(2):
            response = self.client.post(
                "/login/",
                {
                    "username": "nonexistentuser",  # Use non-existent user to trigger failure
                },
            )
            # Should still allow attempts
            self.assertNotEqual(response.status_code, 429)  # Not rate limited yet

        # Account should now be locked
        self.assertTrue(is_account_locked(username="nonexistentuser"))

    def test_webauthn_endpoints_have_cors_headers(self):
        """Test WebAuthn endpoints have appropriate CORS headers."""
        # Test authentication begin endpoint
        response = self.client.post(
            "/custom/passkeys/auth/begin",
            {"username": "testuser"},
            HTTP_ORIGIN="https://atilanogarcia.com",
        )

        # Should have CORS headers (even if endpoint returns error due to missing CSRF)
        # The middleware should still add the headers
        self.assertIn("Access-Control-Allow-Methods", response)

    def test_non_webauthn_endpoints_no_cors(self):
        """Test non-WebAuthn endpoints don't have CORS headers."""
        response = self.client.get("/", HTTP_ORIGIN="https://example.com")

        # Should not have CORS headers
        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertNotIn("Access-Control-Allow-Methods", response)
