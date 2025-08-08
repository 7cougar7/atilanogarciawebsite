"""
Centralized error handling utilities for security-focused error management.
Provides generic user messages while ensuring detailed logging for debugging.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)

# Generic error messages for end users
GENERIC_ERROR_MESSAGES = {
    "authentication_failed": "Authentication failed. Please try again.",
    "authorization_failed": "You are not authorized to access this resource.",
    "invalid_request": "Invalid request. Please check your input and try again.",
    "server_error": "An unexpected error occurred. Please try again later.",
    "rate_limited": "Too many requests. Please wait before trying again.",
    "token_invalid": "Invalid or expired token. Please request a new one.",
    "session_expired": "Your session has expired. Please log in again.",
    "passkey_error": "Passkey operation failed. Please try again.",
    "magic_link_error": "Magic link operation failed. Please try again.",
    "not_found": "Resource not found.",
    "database_error": "Database error occurred.",
}


def log_security_event(
    event_type: str,
    details: Dict[str, Any],
    request=None,
    user=None,
    level: str = "warning",
):
    """
    Log security-related events with consistent formatting and appropriate detail level.

    Args:
        event_type: Type of security event (e.g., 'failed_login', 'rate_limit_exceeded')
        details: Dictionary of event details (will be sanitized)
        request: Django request object (optional)
        user: User object (optional)
        level: Logging level ('info', 'warning', 'error', 'critical')
    """
    # Sanitize sensitive data from details
    sanitized_details = _sanitize_log_data(details)

    # Build log message
    log_parts = [f"Security Event: {event_type}"]

    if user:
        # Handle both user objects and username strings
        if hasattr(user, "username"):
            log_parts.append(f"user={user.username}")
        elif isinstance(user, str):
            log_parts.append(f"user={user}")
        else:
            log_parts.append(f"user={str(user)}")

    if request:
        client_ip = _get_client_ip_safe(request)
        if client_ip:
            log_parts.append(f"ip={client_ip}")

        if hasattr(request, "path"):
            log_parts.append(f"path={request.path}")

    # Add sanitized details
    for key, value in sanitized_details.items():
        log_parts.append(f"{key}={value}")

    log_message = ", ".join(log_parts)

    # Log at appropriate level
    log_func = getattr(logger, level.lower(), logger.warning)
    log_func(log_message)


def handle_view_exception(
    exception: Exception, request=None, user=None, context: str = "view_error"
) -> Dict[str, Any]:
    """
    Handle exceptions in views with secure logging and generic user messages.

    Args:
        exception: The caught exception
        request: Django request object
        user: User object
        context: Context string for logging

    Returns:
        Dictionary with 'user_message' and 'log_details'
    """
    # Generate unique error ID for tracking
    import uuid

    error_id = str(uuid.uuid4())[:8]

    # Log the security event with details
    log_details = {
        "error_id": error_id,
        "error_type": type(exception).__name__,
        "context": context,
        "exception_str": str(exception),
    }

    # In development, include more details
    if settings.DEBUG:
        log_details["traceback"] = traceback.format_exc()

    log_security_event(
        "exception_occurred", log_details, request=request, user=user, level="error"
    )

    # Get generic user message
    message_key = _get_generic_message_for_exception(exception)
    user_message = GENERIC_ERROR_MESSAGES.get(
        message_key, GENERIC_ERROR_MESSAGES["server_error"]
    )

    return {
        "user_message": user_message,
        "error_id": error_id,
        "log_details": log_details,
    }


def secure_json_error_response(
    message_key: str, status_code: int = 400, extra_data: Optional[Dict] = None
) -> JsonResponse:
    """
    Create a secure JSON error response with generic user message.

    Args:
        message_key: Key from GENERIC_ERROR_MESSAGES
        status_code: HTTP status code
        extra_data: Additional data to include in response

    Returns:
        JsonResponse with generic error message
    """
    response_data = {
        "status": "error",
        "message": GENERIC_ERROR_MESSAGES.get(
            message_key, GENERIC_ERROR_MESSAGES["server_error"]
        ),
    }

    if extra_data:
        response_data.update(extra_data)

    return JsonResponse(response_data, status=status_code)


def secure_template_error_response(
    request,
    template_name: str,
    message_key: str,
    extra_context: Optional[Dict] = None,
):
    """
    Render error template with generic user message.

    Args:
        request: Django request object
        template_name: Template to render
        message_key: Key from GENERIC_ERROR_MESSAGES
        extra_context: Additional context for template

    Returns:
        Rendered template response
    """
    context = {
        "error_message": GENERIC_ERROR_MESSAGES.get(
            message_key, GENERIC_ERROR_MESSAGES["server_error"]
        )
    }

    if extra_context:
        context.update(extra_context)

    return render(request, template_name, context)


def _sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove or mask sensitive data from log entries.

    Args:
        data: Dictionary of data to sanitize

    Returns:
        Sanitized dictionary
    """
    sensitive_keys = {
        "password",
        "token",
        "secret",
        "key",
        "credential",
        "session",
        "csrf",
        "auth",
        "signature",
        "hash",
    }

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key contains sensitive terms
        is_sensitive = any(
            sensitive_term in key_lower for sensitive_term in sensitive_keys
        )

        if is_sensitive:
            if isinstance(value, str):
                if len(value) > 8:
                    # Show first 4 and last 4 characters with masking
                    sanitized[key] = f"{value[:4]}***{value[-4:]}"
                elif len(value) > 0:
                    # For shorter strings, just mask completely
                    sanitized[key] = "***MASKED***"
                else:
                    sanitized[key] = "***EMPTY***"
            else:
                sanitized[key] = "***MASKED***"
        else:
            # Limit string length to prevent log bloat
            if isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "...[TRUNCATED]"
            else:
                sanitized[key] = value

    return sanitized


def _get_client_ip_safe(request) -> Optional[str]:
    """
    Safely extract client IP from request.

    Args:
        request: Django request object

    Returns:
        Client IP address or None
    """
    try:
        # Try to get IP from various headers (same logic as rate_limiting.py)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip.strip()

        return request.META.get("REMOTE_ADDR")
    except Exception:
        return None


def _get_generic_message_for_exception(exception: Exception) -> str:
    """
    Map exception types to generic user messages.

    Args:
        exception: The exception to map

    Returns:
        Generic user-friendly message
    """
    exception_type = type(exception).__name__

    # Map specific exception types to generic messages
    exception_mapping = {
        "PermissionDenied": "authorization_failed",
        "AuthenticationFailed": "authentication_failed",
        "ValidationError": "invalid_request",
        "ValueError": "invalid_request",  # Added to handle validation errors
        "ObjectDoesNotExist": "not_found",
        "Http404": "not_found",
        "SuspiciousOperation": "invalid_request",
        "IntegrityError": "database_error",
        "DataError": "database_error",
    }

    return exception_mapping.get(exception_type, "server_error")
