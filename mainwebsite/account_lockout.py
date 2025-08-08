"""
Account lockout system to prevent brute force attacks.
"""

import logging
import time
from datetime import datetime

from django.conf import settings
from django.core.cache import cache

from .rate_limiting import get_client_ip

logger = logging.getLogger(__name__)


class AccountLockoutManager:
    """
    Manages account lockout functionality to prevent brute force attacks.
    """

    # Default settings (can be overridden in Django settings)
    DEFAULT_MAX_ATTEMPTS = 5
    DEFAULT_LOCKOUT_DURATION = 900  # 15 minutes
    DEFAULT_ATTEMPT_WINDOW = 300  # 5 minutes

    @classmethod
    def get_setting(cls, setting_name, default_value):
        """Get setting with fallback to default."""
        return getattr(settings, setting_name, default_value)

    @classmethod
    def get_max_attempts(cls):
        """Get maximum failed attempts before lockout."""
        return cls.get_setting("ACCOUNT_LOCKOUT_MAX_ATTEMPTS", cls.DEFAULT_MAX_ATTEMPTS)

    @classmethod
    def get_lockout_duration(cls):
        """Get lockout duration in seconds."""
        return cls.get_setting("ACCOUNT_LOCKOUT_DURATION", cls.DEFAULT_LOCKOUT_DURATION)

    @classmethod
    def get_attempt_window(cls):
        """Get time window for counting failed attempts in seconds."""
        return cls.get_setting(
            "ACCOUNT_LOCKOUT_ATTEMPT_WINDOW", cls.DEFAULT_ATTEMPT_WINDOW
        )

    @classmethod
    def _get_cache_key(cls, identifier, attempt_type="user"):
        """Generate cache key for lockout tracking."""
        return f"lockout_{attempt_type}_{identifier}"

    @classmethod
    def _get_lockout_key(cls, identifier, attempt_type="user"):
        """Generate cache key for lockout status."""
        return f"locked_{attempt_type}_{identifier}"

    @classmethod
    def record_failed_attempt(cls, username=None, ip_address=None, request=None):
        """
        Record a failed authentication attempt.

        Args:
            username: Username that failed authentication
            ip_address: IP address of the attempt
            request: Django request object (to extract IP if not provided)

        Returns:
            dict: Status information about lockout state
        """
        if request and not ip_address:
            ip_address = get_client_ip(request)

        current_time = time.time()
        max_attempts = cls.get_max_attempts()
        attempt_window = cls.get_attempt_window()
        lockout_duration = cls.get_lockout_duration()

        result = {
            "user_locked": False,
            "ip_locked": False,
            "user_attempts": 0,
            "ip_attempts": 0,
            "lockout_expires": None,
        }

        # Track by username
        if username:
            user_key = cls._get_cache_key(username, "user")
            user_lockout_key = cls._get_lockout_key(username, "user")

            # Get current attempts
            attempts = cache.get(user_key, [])

            # Remove old attempts outside the window
            attempts = [
                attempt
                for attempt in attempts
                if current_time - attempt < attempt_window
            ]

            # Add current attempt
            attempts.append(current_time)
            result["user_attempts"] = len(attempts)

            # Check if user should be locked
            if len(attempts) >= max_attempts:
                lockout_expires = current_time + lockout_duration
                cache.set(user_lockout_key, lockout_expires, lockout_duration)
                result["user_locked"] = True
                result["lockout_expires"] = datetime.fromtimestamp(lockout_expires)

                logger.warning(
                    f"Account locked due to failed attempts: username={username}, "
                    f"attempts={len(attempts)}, ip={ip_address}"
                )
            else:
                # Store updated attempts
                cache.set(user_key, attempts, attempt_window)

        # Track by IP address
        if ip_address:
            ip_key = cls._get_cache_key(ip_address, "ip")
            ip_lockout_key = cls._get_lockout_key(ip_address, "ip")

            # Get current attempts
            attempts = cache.get(ip_key, [])

            # Remove old attempts outside the window
            attempts = [
                attempt
                for attempt in attempts
                if current_time - attempt < attempt_window
            ]

            # Add current attempt
            attempts.append(current_time)
            result["ip_attempts"] = len(attempts)

            # Check if IP should be locked (higher threshold than user)
            ip_max_attempts = max_attempts * 3  # Allow more attempts per IP
            if len(attempts) >= ip_max_attempts:
                lockout_expires = current_time + lockout_duration
                cache.set(ip_lockout_key, lockout_expires, lockout_duration)
                result["ip_locked"] = True
                if not result["lockout_expires"]:
                    result["lockout_expires"] = datetime.fromtimestamp(lockout_expires)

                logger.warning(
                    f"IP address locked due to failed attempts: ip={ip_address}, "
                    f"attempts={len(attempts)}, username={username}"
                )
            else:
                # Store updated attempts
                cache.set(ip_key, attempts, attempt_window)

        return result

    @classmethod
    def is_locked(cls, username=None, ip_address=None, request=None):
        """
        Check if a user or IP address is currently locked.

        Args:
            username: Username to check
            ip_address: IP address to check
            request: Django request object (to extract IP if not provided)

        Returns:
            dict: Lockout status information
        """
        if request and not ip_address:
            ip_address = get_client_ip(request)

        current_time = time.time()
        result = {
            "user_locked": False,
            "ip_locked": False,
            "lockout_expires": None,
            "time_remaining": 0,
        }

        # Check user lockout
        if username:
            user_lockout_key = cls._get_lockout_key(username, "user")
            lockout_expires = cache.get(user_lockout_key)

            if lockout_expires and current_time < lockout_expires:
                result["user_locked"] = True
                result["lockout_expires"] = datetime.fromtimestamp(lockout_expires)
                result["time_remaining"] = int(lockout_expires - current_time)

        # Check IP lockout
        if ip_address:
            ip_lockout_key = cls._get_lockout_key(ip_address, "ip")
            lockout_expires = cache.get(ip_lockout_key)

            if lockout_expires and current_time < lockout_expires:
                result["ip_locked"] = True
                if not result["lockout_expires"]:
                    result["lockout_expires"] = datetime.fromtimestamp(lockout_expires)
                    result["time_remaining"] = int(lockout_expires - current_time)

        return result

    @classmethod
    def clear_failed_attempts(cls, username=None, ip_address=None):
        """
        Clear failed attempts for a user or IP (e.g., after successful login).

        Args:
            username: Username to clear attempts for
            ip_address: IP address to clear attempts for
        """
        if username:
            user_key = cls._get_cache_key(username, "user")
            cache.delete(user_key)

            logger.info(f"Cleared failed attempts for user: {username}")

        if ip_address:
            ip_key = cls._get_cache_key(ip_address, "ip")
            cache.delete(ip_key)

            logger.info(f"Cleared failed attempts for IP: {ip_address}")

    @classmethod
    def unlock_account(cls, username=None, ip_address=None):
        """
        Manually unlock a user account or IP address.

        Args:
            username: Username to unlock
            ip_address: IP address to unlock
        """
        if username:
            user_key = cls._get_cache_key(username, "user")
            user_lockout_key = cls._get_lockout_key(username, "user")
            cache.delete(user_key)
            cache.delete(user_lockout_key)

            logger.info(f"Manually unlocked user account: {username}")

        if ip_address:
            ip_key = cls._get_cache_key(ip_address, "ip")
            ip_lockout_key = cls._get_lockout_key(ip_address, "ip")
            cache.delete(ip_key)
            cache.delete(ip_lockout_key)

            logger.info(f"Manually unlocked IP address: {ip_address}")

    @classmethod
    def get_lockout_status(cls, username=None, ip_address=None, request=None):
        """
        Get detailed lockout status for monitoring/admin purposes.

        Args:
            username: Username to check
            ip_address: IP address to check
            request: Django request object

        Returns:
            dict: Detailed status information
        """
        if request and not ip_address:
            ip_address = get_client_ip(request)

        current_time = time.time()
        attempt_window = cls.get_attempt_window()

        status = {
            "user_attempts": 0,
            "ip_attempts": 0,
            "user_locked": False,
            "ip_locked": False,
            "lockout_expires": None,
            "time_remaining": 0,
        }

        # Get user attempt count
        if username:
            user_key = cls._get_cache_key(username, "user")
            attempts = cache.get(user_key, [])
            # Count recent attempts
            recent_attempts = [a for a in attempts if current_time - a < attempt_window]
            status["user_attempts"] = len(recent_attempts)

        # Get IP attempt count
        if ip_address:
            ip_key = cls._get_cache_key(ip_address, "ip")
            attempts = cache.get(ip_key, [])
            # Count recent attempts
            recent_attempts = [a for a in attempts if current_time - a < attempt_window]
            status["ip_attempts"] = len(recent_attempts)

        # Check lockout status
        lockout_info = cls.is_locked(username, ip_address)
        status.update(lockout_info)

        return status


def is_account_locked(username=None, ip_address=None, request=None):
    """
    Convenience function to check if account is locked.

    Returns:
        bool: True if account is locked, False otherwise
    """
    status = AccountLockoutManager.is_locked(username, ip_address, request)
    return status["user_locked"] or status["ip_locked"]


def record_failed_login(username=None, ip_address=None, request=None):
    """
    Convenience function to record a failed login attempt.

    Returns:
        dict: Lockout status after recording the attempt
    """
    return AccountLockoutManager.record_failed_attempt(username, ip_address, request)


def clear_login_attempts(username=None, ip_address=None, request=None):
    """
    Convenience function to clear failed login attempts after successful login.
    """
    if request and not ip_address:
        ip_address = get_client_ip(request)

    AccountLockoutManager.clear_failed_attempts(username, ip_address)
