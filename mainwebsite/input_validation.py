"""
Input validation and URL security utilities for preventing injection attacks
and open redirects.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.html import escape


class InputValidator:
    """
    Comprehensive input validation utilities for security-focused validation.
    """

    # Username validation pattern (alphanumeric, underscore, hyphen, dot)
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

    # Email validation pattern (basic but secure)
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # URL validation pattern
    URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, Optional[str]]:
        """
        Validate username input for security and format compliance.

        Args:
            username: Username string to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not username:
            return False, "Username is required."

        # Length validation
        if len(username) < 3:
            return False, "Username must be at least 3 characters long."

        if len(username) > 150:
            return False, "Username must be 150 characters or less."

        # Pattern validation
        if not cls.USERNAME_PATTERN.match(username):
            return (
                False,
                "Username can only contain letters, numbers, dots, hyphens, and underscores.",
            )

        # Security checks
        if username.startswith(".") or username.endswith("."):
            return False, "Username cannot start or end with a dot."

        if ".." in username:
            return False, "Username cannot contain consecutive dots."

        # Reserved username checks
        reserved_usernames = {
            "admin",
            "root",
            "administrator",
            "system",
            "user",
            "guest",
            "test",
            "demo",
            "api",
            "www",
            "mail",
            "email",
            "support",
            "help",
            "info",
            "contact",
            "about",
            "login",
            "register",
            "signup",
            "signin",
            "logout",
            "profile",
            "account",
            "settings",
        }

        if username.lower() in reserved_usernames:
            return False, "This username is reserved and cannot be used."

        return True, None

    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email input for security and format compliance.

        Args:
            email: Email string to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not email:
            return False, "Email is required."

        # Length validation
        if len(email) > 254:  # RFC 5321 limit
            return False, "Email address is too long."

        # Pattern validation
        if not cls.EMAIL_PATTERN.match(email):
            return False, "Please enter a valid email address."

        # Additional security checks
        if ".." in email:
            return False, "Email address cannot contain consecutive dots."

        return True, None

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL input for security and format compliance.

        Args:
            url: URL string to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not url:
            return False, "URL is required."

        # Length validation
        if len(url) > 2048:  # Reasonable URL length limit
            return False, "URL is too long."

        # Basic pattern validation
        if not cls.URL_PATTERN.match(url):
            return False, "Please enter a valid URL starting with http:// or https://."

        # Use Django's URL validator for additional checks
        try:
            validator = URLValidator()
            validator(url)
        except ValidationError:
            return False, "Please enter a valid URL."

        # Security checks
        parsed = urlparse(url)

        # Block dangerous schemes
        if parsed.scheme not in ["http", "https"]:
            return False, "Only HTTP and HTTPS URLs are allowed."

        # Block localhost and private IPs in production only
        if not getattr(settings, "DEBUG", False):
            if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
                return False, "Localhost URLs are not allowed."

            # Block private IP ranges
            if parsed.hostname and cls._is_private_ip(parsed.hostname):
                return False, "Private IP addresses are not allowed."

        return True, None

    @classmethod
    def _is_private_ip(cls, hostname: str) -> bool:
        """Check if hostname is a private IP address."""
        try:
            import ipaddress

            ip = ipaddress.ip_address(hostname)
            return ip.is_private
        except ValueError:
            return False

    @classmethod
    def sanitize_input(cls, input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize input string to prevent XSS and other injection attacks.

        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            str: Sanitized string
        """
        if not input_str:
            return ""

        # Truncate if too long
        if len(input_str) > max_length:
            input_str = input_str[:max_length]

        # Remove dangerous patterns before HTML escaping
        dangerous_patterns = [
            ("javascript:", "blocked-javascript:"),
            ("data:", "blocked-data:"),
            ("vbscript:", "blocked-vbscript:"),
            ("file:", "blocked-file:"),
            ("onerror=", "blocked-onerror="),
            ("onload=", "blocked-onload="),
            ("onclick=", "blocked-onclick="),
            ("onmouseover=", "blocked-onmouseover="),
        ]

        sanitized = input_str
        for pattern, replacement in dangerous_patterns:
            sanitized = sanitized.replace(pattern, replacement)
            sanitized = sanitized.replace(pattern.upper(), replacement)

        # HTML escape to prevent XSS
        sanitized = escape(sanitized)

        # Remove null bytes and other control characters
        sanitized = "".join(
            char for char in sanitized if ord(char) >= 32 or char in "\t\n\r"
        )

        return sanitized.strip()


class RedirectValidator:
    """
    URL redirect validation utilities to prevent open redirect attacks.
    """

    @classmethod
    def validate_redirect_url(cls, url: str, request=None) -> Tuple[bool, str]:
        """
        Validate and sanitize redirect URLs to prevent open redirect attacks.

        Args:
            url: URL to validate for redirection
            request: Django request object (optional, for domain validation)

        Returns:
            tuple: (is_safe, safe_url)
        """
        if not url:
            return True, "/"

        # Remove any leading/trailing whitespace
        url = url.strip()

        # Handle relative URLs (these are generally safe)
        if url.startswith("/") and not url.startswith("//"):
            # Ensure it's a valid path
            if cls._is_valid_path(url):
                return True, url
            else:
                return False, "/"

        # Parse the URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "/"

        # Block URLs with schemes (absolute URLs)
        if parsed.scheme:
            # Only allow same-origin redirects if we have a request
            if request:
                current_host = request.get_host()
                if parsed.netloc == current_host:
                    return True, url

            # Block all external redirects
            return False, "/"

        # Handle protocol-relative URLs (//example.com)
        if url.startswith("//"):
            return False, "/"

        # For any other case, default to safe redirect
        return False, "/"

    @classmethod
    def _is_valid_path(cls, path: str) -> bool:
        """
        Check if a path is valid and safe for redirection.

        Args:
            path: URL path to validate

        Returns:
            bool: True if path is safe
        """
        # Block paths with dangerous patterns
        dangerous_patterns = [
            "..",
            "\\",
            "\x00",
            "\r",
            "\n",
            "\t",
            "javascript:",
            "data:",
            "vbscript:",
            "file:",
            "<script",
            "</script>",
            "onclick",
            "onerror",
        ]

        path_lower = path.lower()
        for pattern in dangerous_patterns:
            if pattern in path_lower:
                return False

        # Ensure path doesn't exceed reasonable length
        if len(path) > 1000:
            return False

        return True

    @classmethod
    def get_safe_redirect_url(
        cls, next_param: str, default_url: str = "/", request=None
    ) -> str:
        """
        Get a safe redirect URL from user input.

        Args:
            next_param: The 'next' parameter from user input
            default_url: Default URL to use if validation fails
            request: Django request object (optional)

        Returns:
            str: Safe redirect URL
        """
        is_safe, safe_url = cls.validate_redirect_url(next_param, request)
        return safe_url if is_safe else default_url

    @classmethod
    def get_whitelisted_redirect_url(
        cls, next_param: str, allowed_urls: list = None, default_url: str = "/"
    ) -> str:
        """
        Get redirect URL from a whitelist of allowed URLs.

        Args:
            next_param: The 'next' parameter from user input
            allowed_urls: List of allowed redirect URLs/patterns
            default_url: Default URL to use if validation fails

        Returns:
            str: Safe redirect URL
        """
        if not next_param:
            return default_url

        # Default allowed URLs if none provided
        if allowed_urls is None:
            allowed_urls = [
                "/",
                "/personal-ai/",
                "/passkeys-register/",
                "/login/",
                "/logout/",
            ]

        # Check if the URL is in the whitelist
        for allowed_url in allowed_urls:
            if next_param == allowed_url:
                return next_param

            # Allow pattern matching for dynamic URLs
            if allowed_url.endswith("*") and next_param.startswith(allowed_url[:-1]):
                return next_param

        return default_url


# Convenience functions for common validation tasks
def validate_username_input(username: str) -> Tuple[bool, Optional[str]]:
    """Validate username input."""
    return InputValidator.validate_username(username)


def validate_email_input(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email input."""
    return InputValidator.validate_email(email)


def validate_url_input(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL input."""
    return InputValidator.validate_url(url)


def sanitize_user_input(input_str: str, max_length: int = 1000) -> str:
    """Sanitize user input."""
    return InputValidator.sanitize_input(input_str, max_length)


def get_safe_redirect_url(next_param: str, default_url: str = "/", request=None) -> str:
    """Get safe redirect URL."""
    return RedirectValidator.get_safe_redirect_url(next_param, default_url, request)


def get_whitelisted_redirect_url(
    next_param: str, allowed_urls: list = None, default_url: str = "/"
) -> str:
    """Get whitelisted redirect URL."""
    return RedirectValidator.get_whitelisted_redirect_url(
        next_param, allowed_urls, default_url
    )
