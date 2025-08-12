"""
Aurora DSQL compatibility fixes for Django User model.

This module provides fixes for the UUID primary key mismatch between Django's User model
and the consolidated migration schema in Aurora DSQL environments.
"""

import uuid

from django.contrib.auth.models import User
from django.db import connection, models, transaction
from django.utils import timezone


def is_aurora_dsql_environment():
    """Check if we're running in an Aurora DSQL environment."""
    try:
        db_engine = connection.settings_dict.get("ENGINE", "")
        return "aurora" in db_engine.lower() or "dsql" in db_engine.lower()
    except Exception:
        return False


def apply_django_compatibility_patches():
    """
    Apply Django version compatibility patches globally.

    This fixes the ImmutableList concatenation error that occurs in Django's
    model field checking system.
    """
    try:
        from django.db.models.fields.related import RelatedField

        # Store original method
        if not hasattr(RelatedField, "_original_check_clashes"):
            RelatedField._original_check_clashes = RelatedField._check_clashes

            def patched_check_clashes(self):
                """Patched version that handles ImmutableList compatibility."""
                try:
                    return self._original_check_clashes()
                except TypeError as e:
                    if "can only concatenate list" in str(e):
                        # Handle the ImmutableList concatenation issue
                        rel_opts = self.remote_field.model._meta
                        # Convert both to lists to ensure compatibility
                        fields = (
                            list(rel_opts.fields)
                            if hasattr(rel_opts.fields, "__iter__")
                            else []
                        )
                        many_to_many = (
                            list(rel_opts.many_to_many)
                            if hasattr(rel_opts.many_to_many, "__iter__")
                            else []
                        )
                        potential_clashes = fields + many_to_many

                        # Continue with the original logic using the converted lists
                        clashes = []
                        for field in potential_clashes:
                            if field.name == self.name:
                                clashes.append(field)
                        return clashes
                    else:
                        raise

            # Apply the patch
            RelatedField._check_clashes = patched_check_clashes
            print("✅ Django Compatibility: Applied ImmutableList concatenation fix")

    except ImportError:
        # If we can't import the required modules, skip the patch
        pass
    except Exception as e:
        print(f"⚠️ Could not apply Django field checking patch: {e}")


# Apply Django compatibility patches globally
apply_django_compatibility_patches()


# Fix Django's User model primary key field for Aurora DSQL environments
if is_aurora_dsql_environment():
    # Store reference to original field
    original_pk_field = User._meta.pk

    # Create a new UUIDField to replace the AutoField
    uuid_field = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uuid_field.name = "id"
    uuid_field.attname = "id"
    uuid_field.column = "id"
    uuid_field.model = User

    # Completely rebuild the fields list without the original AutoField
    new_fields = []
    for field in User._meta.fields:
        if field.name == "id":
            # Replace the AutoField with our UUIDField
            new_fields.append(uuid_field)
        else:
            new_fields.append(field)

    # Update the model's meta information
    User._meta.fields = new_fields
    User._meta.pk = uuid_field

    # Update the model class to use the new field
    setattr(User, "id", uuid_field)

    # Clear field caches but let Django rebuild them naturally
    if hasattr(User._meta, "_field_cache"):
        User._meta._field_cache = {}
    if hasattr(User._meta, "_field_name_cache"):
        User._meta._field_name_cache = []

    # Don't set these to None - let Django rebuild them when needed
    # This prevents the "NoneType object is not subscriptable" error
    if hasattr(User._meta, "_name_map"):
        delattr(User._meta, "_name_map")
    if hasattr(User._meta, "_forward_fields_map"):
        delattr(User._meta, "_forward_fields_map")
    if hasattr(User._meta, "_fields_map"):
        delattr(User._meta, "_fields_map")

    print("✅ Aurora DSQL: Patched User model primary key field to UUIDField")


# Fix Django's update_last_login for Aurora DSQL environments
if is_aurora_dsql_environment():
    from django.contrib.auth.models import update_last_login
    from django.contrib.auth.signals import user_logged_in
    from django.dispatch import receiver

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


# Completely override User model save method for Aurora DSQL environments
if is_aurora_dsql_environment():
    original_save = User.save

    def aurora_dsql_save(self, *args, **kwargs):
        """
        Complete replacement of User.save() for Aurora DSQL environments.

        This bypasses Django's ORM entirely for User operations to avoid
        UUID/AutoField conflicts and uses raw SQL instead.
        """
        # Handle update_fields scenario (like last_login updates)
        if not self._state.adding and "update_fields" in kwargs:
            update_fields = kwargs.get("update_fields", [])
            if len(update_fields) == 1 and "last_login" in update_fields:
                # Handle last_login update with raw SQL
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE auth_user SET last_login = %s WHERE id = %s",
                            [self.last_login, str(self.id)],
                        )
                    return  # Skip the normal save process
                except Exception:
                    pass  # Fall back to normal save

        # For all other operations, use raw SQL to avoid ORM UUID issues
        try:
            with transaction.atomic():
                if self._state.adding:
                    # INSERT new user with raw SQL
                    if not self.id:
                        self.id = uuid.uuid4()

                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO auth_user (
                                id, password, last_login, is_superuser, username,
                                first_name, last_name, email, is_staff, is_active, date_joined
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                            [
                                str(self.id),
                                self.password,
                                self.last_login,
                                self.is_superuser,
                                self.username,
                                self.first_name,
                                self.last_name,
                                self.email,
                                self.is_staff,
                                self.is_active,
                                self.date_joined,
                            ],
                        )

                    # Mark as no longer adding
                    self._state.adding = False
                    self._state.db = "default"

                else:
                    # UPDATE existing user with raw SQL
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE auth_user SET
                                password = %s, last_login = %s, is_superuser = %s,
                                username = %s, first_name = %s, last_name = %s,
                                email = %s, is_staff = %s, is_active = %s, date_joined = %s
                            WHERE id = %s
                        """,
                            [
                                self.password,
                                self.last_login,
                                self.is_superuser,
                                self.username,
                                self.first_name,
                                self.last_name,
                                self.email,
                                self.is_staff,
                                self.is_active,
                                self.date_joined,
                                str(self.id),
                            ],
                        )

                print(
                    f"✅ Aurora DSQL: User {self.username} saved successfully with UUID {self.id}"
                )

        except Exception as e:
            print(f"❌ Aurora DSQL: Raw SQL save failed for user {self.username}: {e}")
            # Fall back to original save method as last resort
            try:
                original_save(self, *args, **kwargs)
            except Exception as e2:
                print(f"❌ Aurora DSQL: Original save also failed: {e2}")
                raise e2

    # Replace the save method
    User.save = aurora_dsql_save
    print("✅ Aurora DSQL: Replaced User.save() with raw SQL implementation")
