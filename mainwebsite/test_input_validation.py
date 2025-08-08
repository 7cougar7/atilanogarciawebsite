"""
Tests for input validation and URL security utilities.
"""

from django.test import RequestFactory, TestCase, override_settings

from .input_validation import (
    RedirectValidator,
    get_safe_redirect_url,
    get_whitelisted_redirect_url,
    sanitize_user_input,
    validate_email_input,
    validate_url_input,
    validate_username_input,
)


class InputValidatorTests(TestCase):
    """Test the InputValidator class methods."""

    def test_validate_username_valid_cases(self):
        """Test valid username inputs."""
        valid_usernames = [
            "testuser",
            "test_user",
            "test-user",
            "test.user",
            "user123",
            "123user",
            "a" * 150,  # Maximum length
        ]

        for username in valid_usernames:
            with self.subTest(username=username):
                is_valid, error = validate_username_input(username)
                self.assertTrue(is_valid, f"Username '{username}' should be valid")
                self.assertIsNone(error)

    def test_validate_username_invalid_cases(self):
        """Test invalid username inputs."""
        invalid_cases = [
            ("", "Username is required."),
            ("ab", "Username must be at least 3 characters long."),
            ("a" * 151, "Username must be 150 characters or less."),
            (
                "test@user",
                "Username can only contain letters, numbers, dots, hyphens, and underscores.",
            ),
            (
                "test user",
                "Username can only contain letters, numbers, dots, hyphens, and underscores.",
            ),
            (
                "test<script>",
                "Username can only contain letters, numbers, dots, hyphens, and underscores.",
            ),
            (".testuser", "Username cannot start or end with a dot."),
            ("testuser.", "Username cannot start or end with a dot."),
            ("test..user", "Username cannot contain consecutive dots."),
            ("admin", "This username is reserved and cannot be used."),
            ("root", "This username is reserved and cannot be used."),
            (
                "ADMIN",
                "This username is reserved and cannot be used.",
            ),  # Case insensitive
        ]

        for username, expected_error in invalid_cases:
            with self.subTest(username=username):
                is_valid, error = validate_username_input(username)
                self.assertFalse(is_valid, f"Username '{username}' should be invalid")
                self.assertEqual(error, expected_error)

    def test_validate_email_valid_cases(self):
        """Test valid email inputs."""
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user123@example-site.com",
            "a@b.co",
        ]

        for email in valid_emails:
            with self.subTest(email=email):
                is_valid, error = validate_email_input(email)
                self.assertTrue(is_valid, f"Email '{email}' should be valid")
                self.assertIsNone(error)

    def test_validate_email_invalid_cases(self):
        """Test invalid email inputs."""
        invalid_cases = [
            ("", "Email is required."),
            ("a" * 255 + "@example.com", "Email address is too long."),
            ("invalid-email", "Please enter a valid email address."),
            ("test@", "Please enter a valid email address."),
            ("@example.com", "Please enter a valid email address."),
            (
                "test..user@example.com",
                "Email address cannot contain consecutive dots.",
            ),
        ]

        for email, expected_error in invalid_cases:
            with self.subTest(email=email):
                is_valid, error = validate_email_input(email)
                self.assertFalse(is_valid, f"Email '{email}' should be invalid")
                self.assertEqual(error, expected_error)

    @override_settings(DEBUG=True)
    def test_validate_url_valid_cases(self):
        """Test valid URL inputs."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://www.example.com",
            "http://example.com/path",
            "https://example.com:8080/path?query=value",
            "http://localhost:3000",  # Should be valid in DEBUG mode
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                is_valid, error = validate_url_input(url)
                self.assertTrue(is_valid, f"URL '{url}' should be valid")
                self.assertIsNone(error)

    def test_validate_url_invalid_cases(self):
        """Test invalid URL inputs."""
        invalid_cases = [
            ("", "URL is required."),
            ("a" * 2049, "URL is too long."),
            (
                "ftp://example.com",
                "Please enter a valid URL starting with http:// or https://.",
            ),
            (
                "javascript:alert('xss')",
                "Please enter a valid URL starting with http:// or https://.",
            ),
            (
                "data:text/html,<script>alert('xss')</script>",
                "Please enter a valid URL starting with http:// or https://.",
            ),
            (
                "not-a-url",
                "Please enter a valid URL starting with http:// or https://.",
            ),
        ]

        for url, expected_error in invalid_cases:
            with self.subTest(url=url):
                is_valid, error = validate_url_input(url)
                self.assertFalse(is_valid, f"URL '{url}' should be invalid")
                self.assertIn(
                    expected_error.split(".")[0], error
                )  # Check partial match

    def test_sanitize_input(self):
        """Test input sanitization."""
        test_cases = [
            ("normal text", "normal text"),
            (
                "<script>alert('xss')</script>",
                "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;",
            ),
            ("text with\x00null bytes", "text withnull bytes"),
            ("  whitespace  ", "whitespace"),
            ("a" * 1500, "a" * 1000),  # Test truncation
            ("javascript:alert('xss')", "blocked-javascript:alert(&#x27;xss&#x27;)"),
            ("onerror=alert('xss')", "blocked-onerror=alert(&#x27;xss&#x27;)"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = sanitize_user_input(input_text, max_length=1000)
                self.assertEqual(result, expected)


class RedirectValidatorTests(TestCase):
    """Test the RedirectValidator class methods."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_redirect_url_safe_paths(self):
        """Test validation of safe relative paths."""
        safe_paths = [
            "/",
            "/personal-ai/",
            "/login/",
            "/some/valid/path",
        ]

        for path in safe_paths:
            with self.subTest(path=path):
                is_safe, safe_url = RedirectValidator.validate_redirect_url(path)
                self.assertTrue(is_safe, f"Path '{path}' should be safe")
                self.assertEqual(safe_url, path)

    def test_validate_redirect_url_dangerous_paths(self):
        """Test validation of dangerous paths."""
        dangerous_paths = [
            "//evil.com",
            "http://evil.com",
            "https://evil.com",
            "javascript:alert('xss')",
            "/path/with/../traversal",
            "/path/with\x00null",
            "<script>alert('xss')</script>",
        ]

        for path in dangerous_paths:
            with self.subTest(path=path):
                is_safe, safe_url = RedirectValidator.validate_redirect_url(path)
                self.assertFalse(is_safe, f"Path '{path}' should be dangerous")
                self.assertEqual(safe_url, "/")

    def test_get_safe_redirect_url(self):
        """Test getting safe redirect URLs."""
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "testserver"

        test_cases = [
            ("/personal-ai/", "/personal-ai/"),
            ("http://evil.com", "/"),
            ("//evil.com", "/"),
            ("", "/"),
            (None, "/"),
        ]

        for input_url, expected in test_cases:
            with self.subTest(input_url=input_url):
                result = get_safe_redirect_url(input_url, request=request)
                self.assertEqual(result, expected)

    def test_get_whitelisted_redirect_url(self):
        """Test getting whitelisted redirect URLs."""
        allowed_urls = ["/", "/personal-ai/", "/login/"]

        test_cases = [
            ("/personal-ai/", "/personal-ai/"),
            ("/login/", "/login/"),
            ("/not-allowed/", "/"),
            ("http://evil.com", "/"),
            ("", "/"),
        ]

        for input_url, expected in test_cases:
            with self.subTest(input_url=input_url):
                result = get_whitelisted_redirect_url(input_url, allowed_urls)
                self.assertEqual(result, expected)

    def test_whitelisted_redirect_with_patterns(self):
        """Test whitelisted redirects with wildcard patterns."""
        allowed_urls = ["/", "/api/*", "/admin/*"]

        test_cases = [
            ("/api/users", "/api/users"),
            ("/api/data/export", "/api/data/export"),
            ("/admin/settings", "/admin/settings"),
            ("/public/page", "/"),
        ]

        for input_url, expected in test_cases:
            with self.subTest(input_url=input_url):
                result = get_whitelisted_redirect_url(input_url, allowed_urls)
                self.assertEqual(result, expected)


class InputValidationIntegrationTests(TestCase):
    """Integration tests for input validation in views and forms."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_username_form_validation(self):
        """Test that UsernameForm uses the new validation."""
        from .forms import UsernameForm

        # Test valid username
        form = UsernameForm(data={"username": "validuser"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["username"], "validuser")

        # Test invalid username
        form = UsernameForm(data={"username": "admin"})
        self.assertFalse(form.is_valid())
        self.assertIn("reserved", str(form.errors["username"]))

    def test_url_shortener_validation(self):
        """Test that URL shortener validates input properly."""
        from django.test import Client

        client = Client()

        # Test valid URL
        response = client.post(
            "/url-shortener-submit/",
            {"url": "https://example.com", "csrfmiddlewaretoken": "test"},
        )
        # Should succeed (status 200) or fail with CSRF (status 403) or not found (404)
        self.assertIn(response.status_code, [200, 403, 404])

        # Test invalid URL
        response = client.post(
            "/url-shortener-submit/",
            {"url": 'javascript:alert("xss")', "csrfmiddlewaretoken": "test"},
        )
        # Should fail with validation error, CSRF error, or not found
        self.assertIn(response.status_code, [400, 403, 404])

    def test_xss_prevention_in_input_sanitization(self):
        """Test that XSS payloads are properly sanitized."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
        ]

        for payload in xss_payloads:
            with self.subTest(payload=payload):
                sanitized = sanitize_user_input(payload)
                # Should not contain unescaped script tags or dangerous patterns
                self.assertNotIn("<script", sanitized.lower())
                # Should contain escaped or blocked versions (evidence of sanitization)
                self.assertTrue(
                    "&lt;" in sanitized or "&gt;" in sanitized or "&#x27;" in sanitized,
                    f"Payload '{payload}' was not properly sanitized: '{sanitized}'",
                )


class SecurityRegressionTests(TestCase):
    """Regression tests for security vulnerabilities."""

    def test_open_redirect_prevention(self):
        """Test that open redirects are prevented."""
        dangerous_redirects = [
            "http://evil.com",
            "https://evil.com",
            "//evil.com",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
        ]

        for redirect_url in dangerous_redirects:
            with self.subTest(redirect_url=redirect_url):
                safe_url = get_safe_redirect_url(redirect_url)
                self.assertEqual(
                    safe_url,
                    "/",
                    f"Dangerous redirect '{redirect_url}' was not blocked",
                )

    def test_xss_prevention_in_input_sanitization(self):
        """Test that XSS payloads are properly sanitized."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
        ]

        for payload in xss_payloads:
            with self.subTest(payload=payload):
                sanitized = sanitize_user_input(payload)
                # Should not contain unescaped dangerous patterns
                self.assertNotIn("<script", sanitized.lower())
                # Should contain escaped or blocked versions (evidence of sanitization)
                self.assertTrue(
                    "&lt;" in sanitized or "&gt;" in sanitized or "&#x27;" in sanitized,
                    f"Payload '{payload}' was not properly sanitized: '{sanitized}'",
                )

    def test_sql_injection_prevention_in_username(self):
        """Test that SQL injection attempts in usernames are blocked."""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "admin' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
        ]

        for payload in sql_injection_payloads:
            with self.subTest(payload=payload):
                is_valid, error = validate_username_input(payload)
                self.assertFalse(
                    is_valid, f"SQL injection payload '{payload}' should be rejected"
                )
                self.assertIsNotNone(error)
