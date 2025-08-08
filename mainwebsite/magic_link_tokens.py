"""
Custom token generator for magic links with explicit expiration and enhanced security
"""

import hashlib
import time

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare


class MagicLinkTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom token generator for magic links with explicit expiration time.

    Extends Django's PasswordResetTokenGenerator with additional security features.
    """

    def __init__(self):
        super().__init__()
        # Magic link expiration time (15 minutes by default)
        self.timeout = getattr(settings, "MAGIC_LINK_TIMEOUT", 900)

    def check_token(self, user, token):
        """
        Check that a magic link token is correct for a given user and hasn't expired.
        """
        if not (user and token):
            return False

        # Parse the token
        try:
            ts_hex, hash_value = token.split("-", 1)
        except ValueError:
            return False

        try:
            ts = int(ts_hex, 16)  # Parse hex timestamp
        except ValueError:
            return False

        # Check if token has expired
        current_time = int(time.time())
        if (current_time - ts) > self.timeout:
            return False

        # Verify token integrity
        expected_hash = self._make_hash_value(user, ts)[:20]
        return constant_time_compare(hash_value, expected_hash)

    def make_token(self, user):
        """
        Generate a token for the given user with current timestamp.
        """
        timestamp = int(time.time())
        return self._make_token_with_timestamp(user, timestamp)

    def _make_token_with_timestamp(self, user, timestamp):
        """
        Generate token with specific timestamp for testing purposes.
        """
        # Convert timestamp to hex string
        ts_hex = format(int(timestamp), "x")

        # Generate hash using user info and timestamp
        hash_value = self._make_hash_value(user, timestamp)[:20]

        return f"{ts_hex}-{hash_value}"

    def _make_hash_value(self, user, timestamp):
        """
        Create hash value using user data and timestamp.
        """
        # Include user ID, email, last login, and timestamp
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        hash_string = (
            f"{user.pk}{user.email}{login_timestamp}{timestamp}{self.key_salt}"
        )
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def get_token_expiration_time(self):
        """
        Get the expiration time in seconds for magic link tokens.
        """
        return self.timeout

    def get_token_expiration_minutes(self):
        """
        Get the expiration time in minutes for display purposes.
        """
        return self.timeout // 60


# Create a global instance
magic_link_token_generator = MagicLinkTokenGenerator()
