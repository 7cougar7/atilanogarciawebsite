"""
Aurora DSQL compatibility fixes for Django User model.

This module provides fixes for the UUID primary key mismatch between Django's User model
and the consolidated migration schema in Aurora DSQL environments.
"""

import uuid

from django.contrib.auth.models import User
from django.db import connection


def is_aurora_dsql_environment():
    """Check if we're running in an Aurora DSQL environment."""
    try:
        db_engine = connection.settings_dict.get("ENGINE", "")
        return "aurora" in db_engine.lower() or "dsql" in db_engine.lower()
    except Exception:
        return False


# Fix Django's update_last_login for Aurora DSQL environments
if is_aurora_dsql_environment():
    from django.contrib.auth.models import update_last_login
    from django.contrib.auth.signals import user_logged_in
    from django.dispatch import receiver
    from django.utils import timezone

    # Disconnect Django's default update_last_login handler
    user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")

    @receiver(user_logged_in, dispatch_uid="aurora_dsql_update_last_login")
    def aurora_dsql_update_last_login(sender, user, request, **kwargs):
        """
        Custom signal handler to update last_login for Aurora DSQL environments.

        This replaces Django's default update_last_login handler that fails due to
        UUID/AutoField primary key mismatch.
        """
        try:
            # Use raw SQL to update the last_login field with UUID primary key
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth_user SET last_login = %s WHERE id = %s",
                    [timezone.now(), str(user.id)],
                )
        except Exception as e:
            # Log the error but don't fail the login process
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update last_login for user {user.username}: {e}")


# Monkey patch the User model's save method to handle UUID primary keys
if is_aurora_dsql_environment():
    original_save = User.save

    def aurora_dsql_save(self, *args, **kwargs):
        """
        Custom save method for Aurora DSQL environments that handles UUID primary keys.
        """
        # If this is a new user being created and no ID is set, generate a UUID
        if self._state.adding and not self.id:
            self.id = uuid.uuid4()

        # For updates, check if we need to handle the UUID/AutoField mismatch
        if not self._state.adding and "update_fields" in kwargs:
            update_fields = kwargs.get("update_fields", [])
            if "last_login" in update_fields:
                # Handle last_login update manually with raw SQL
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE auth_user SET last_login = %s WHERE id = %s",
                            [self.last_login, str(self.id)],
                        )
                    return  # Skip the normal save process
                except Exception:
                    pass  # Fall back to normal save

        # Call the original save method
        original_save(self, *args, **kwargs)

    # Replace the save method
    User.save = aurora_dsql_save
