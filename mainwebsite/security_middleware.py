"""
Security middleware for enhanced security headers and CORS configuration.
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add comprehensive security headers to all responses.
    """

    def process_response(self, request, response):
        """Add security headers to response."""

        # Content Security Policy (CSP)
        # Allow self for scripts, styles, and images, plus specific domains for WebAuthn and external resources
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "media-src 'self' https://content.atilanogarcia.com",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        # Only add upgrade-insecure-requests in production to avoid localhost HTTP issues
        if not settings.DEBUG:
            csp_directives.append("upgrade-insecure-requests")

        csp_policy = "; ".join(csp_directives)
        response["Content-Security-Policy"] = csp_policy

        # Referrer Policy - limit information sent in referrer header
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        # Disable potentially dangerous features
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "encrypted-media=(), "
            "fullscreen=(self), "
            "picture-in-picture=()"
        )
        response["Permissions-Policy"] = permissions_policy

        # Cross-Origin Embedder Policy
        # In development, use unsafe-none to avoid static file loading issues
        # In production, use require-corp for security
        if settings.DEBUG:
            response["Cross-Origin-Embedder-Policy"] = "unsafe-none"
        else:
            response["Cross-Origin-Embedder-Policy"] = "require-corp"

        # Cross-Origin Opener Policy
        response["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin Resource Policy
        # In development, use cross-origin to avoid static file loading issues
        # In production, use cross-origin to allow content from subdomains like content.atilanogarcia.com
        response["Cross-Origin-Resource-Policy"] = "cross-origin"

        # Additional security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"

        # Remove server information
        if "Server" in response:
            del response["Server"]

        return response


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware specifically for WebAuthn endpoints.
    """

    def process_request(self, request):
        """Handle preflight OPTIONS requests for CORS."""
        if request.method == "OPTIONS":
            # Check if this is a WebAuthn endpoint
            webauthn_paths = [
                "/custom/passkeys/auth/begin",
                "/custom/passkeys/auth/complete",
                "/custom/passkeys/reg/begin",
                "/custom/passkeys/reg/complete",
            ]

            if any(request.path.startswith(path) for path in webauthn_paths):
                response = HttpResponse()
                self._add_cors_headers(request, response)
                return response

        return None

    def process_response(self, request, response):
        """Add CORS headers to WebAuthn endpoint responses."""
        webauthn_paths = [
            "/custom/passkeys/auth/begin",
            "/custom/passkeys/auth/complete",
            "/custom/passkeys/reg/begin",
            "/custom/passkeys/reg/complete",
        ]

        if any(request.path.startswith(path) for path in webauthn_paths):
            self._add_cors_headers(request, response)

        return response

    def _add_cors_headers(self, request, response):
        """Add CORS headers for WebAuthn endpoints."""
        # Get the origin from the request
        origin = request.META.get("HTTP_ORIGIN", "")

        # Define allowed origins for WebAuthn (should match your domains)
        allowed_origins = [
            "https://atilanogarcia.com",
            "https://www.atilanogarcia.com",
            "https://tilogarcia.com",
            "https://www.tilogarcia.com",
            "https://tilog.me",
            "https://www.tilog.me",
        ]

        # In development, allow localhost
        if settings.DEBUG:
            allowed_origins.extend(
                [
                    "http://localhost:8000",
                    "http://127.0.0.1:8000",
                    "https://localhost:8000",
                    "https://127.0.0.1:8000",
                ]
            )

        # Check if origin is allowed
        if origin in allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
        elif settings.DEBUG and origin.startswith(
            ("http://localhost", "https://localhost")
        ):
            # Allow any localhost port in development
            response["Access-Control-Allow-Origin"] = origin

        # WebAuthn specific headers
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Content-Type, X-CSRFToken, X-Requested-With, Authorization"
        )
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Max-Age"] = "86400"  # 24 hours

        # Ensure WebAuthn responses are not cached
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
