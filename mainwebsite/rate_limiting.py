"""
Rate limiting utilities for magic link requests
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import MagicLinkRequest

logger = logging.getLogger(__name__)


class MagicLinkRateLimiter:
    """
    Rate limiter for magic link requests to prevent abuse
    """

    def __init__(self):
        self.per_user_limit = getattr(settings, "MAGIC_LINK_RATE_LIMIT_PER_USER", 3)
        self.per_ip_limit = getattr(settings, "MAGIC_LINK_RATE_LIMIT_PER_IP", 10)
        self.window_seconds = getattr(settings, "MAGIC_LINK_RATE_LIMIT_WINDOW", 3600)

    def is_rate_limited(self, user, ip_address):
        """
        Check if a user or IP address is rate limited.

        Args:
            user: Django User instance
            ip_address: IP address string

        Returns:
            tuple: (is_limited, reason, retry_after_seconds)
        """
        current_time = timezone.now()
        window_start = current_time - timedelta(seconds=self.window_seconds)

        # Check user-based rate limit
        if user:
            user_requests = MagicLinkRequest.objects.filter(
                user=user, requested_at__gte=window_start, success=True
            ).count()

            if user_requests >= self.per_user_limit:
                # Calculate retry after time based on oldest request in window
                oldest_request = (
                    MagicLinkRequest.objects.filter(
                        user=user, requested_at__gte=window_start, success=True
                    )
                    .order_by("requested_at")
                    .first()
                )

                if oldest_request:
                    retry_after = self.window_seconds - int(
                        (current_time - oldest_request.requested_at).total_seconds()
                    )
                    return (
                        True,
                        f"Too many magic link requests. Try again in {retry_after // 60} minutes.",
                        retry_after,
                    )

        # Check IP-based rate limit
        ip_requests = MagicLinkRequest.objects.filter(
            ip_address=ip_address, requested_at__gte=window_start, success=True
        ).count()

        if ip_requests >= self.per_ip_limit:
            # Calculate retry after time based on oldest request in window
            oldest_request = (
                MagicLinkRequest.objects.filter(
                    ip_address=ip_address, requested_at__gte=window_start, success=True
                )
                .order_by("requested_at")
                .first()
            )

            if oldest_request:
                retry_after = self.window_seconds - int(
                    (current_time - oldest_request.requested_at).total_seconds()
                )
                return (
                    True,
                    f"Too many magic link requests from this IP. Try again in {retry_after // 60} minutes.",
                    retry_after,
                )

        return False, None, 0

    def record_request(self, user, email, ip_address, user_agent="", success=True):
        """
        Record a magic link request for rate limiting and monitoring.

        Args:
            user: Django User instance
            email: Email address
            ip_address: IP address string
            user_agent: User agent string
            success: Whether the request was successful
        """
        try:
            MagicLinkRequest.objects.create(
                user=user,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent[:1000],  # Limit user agent length
                success=success,
            )

            logger.info(
                f"Magic link request recorded: user={user.username if user else 'None'}, "
                f"email={email}, ip={ip_address}, success={success}"
            )
        except Exception as e:
            logger.error(f"Failed to record magic link request: {e}")

    def cleanup_old_requests(self, days=30):
        """
        Clean up old magic link requests to prevent database bloat.

        Args:
            days: Number of days to keep records (default: 30)
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = MagicLinkRequest.objects.filter(
            requested_at__lt=cutoff_date
        ).delete()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old magic link requests")

        return deleted_count


# Global rate limiter instance
magic_link_rate_limiter = MagicLinkRateLimiter()


def get_client_ip(request):
    """
    Get the client IP address from the request, handling proxies.

    Args:
        request: Django HttpRequest object

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    return ip


def get_user_agent(request):
    """
    Get the user agent string from the request.

    Args:
        request: Django HttpRequest object

    Returns:
        str: User agent string
    """
    return request.META.get("HTTP_USER_AGENT", "")
