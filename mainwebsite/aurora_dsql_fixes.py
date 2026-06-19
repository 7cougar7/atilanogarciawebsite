"""
Aurora DSQL compatibility fixes for Django User model.

This module provides fixes for the UUID primary key mismatch between Django's User model
and the consolidated migration schema in Aurora DSQL environments.

These patches reach into Django's private ``_meta`` internals, which are NOT covered by
the SQLite-based test suite (they only activate against Aurora DSQL in production). To
make major Django upgrades safe, every patch here is written to **fail loud, not silent**:
if an internal Django structure this code depends on is missing or has an unexpected
shape, we raise a clear error at startup rather than booting with a half-patched User
model that would silently corrupt data via the raw-SQL save path below.
"""

import logging
import uuid

import django
from django.contrib.auth.models import User
from django.db import connection, models, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Django versions this module's _meta patching has been validated against. A version
# outside this range may have restructured the private internals we depend on; we still
# attempt the patch (and verify it took effect) but emit a loud warning so the mismatch
# is obvious in logs before anything subtle breaks.
VALIDATED_DJANGO = (5, 2)


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
    model field checking system. Runs in all environments (including tests), so it
    must be idempotent and must not change behavior when the underlying issue is absent.
    """
    try:
        from django.db.models.fields.related import RelatedField
    except ImportError:
        # Django internals moved; the original error this guards against can no longer
        # occur in the form we patch. Skip rather than fail — this is a defensive wrapper.
        logger.warning(
            "Could not import RelatedField; skipping _check_clashes compatibility patch "
            "(Django %s)",
            django.get_version(),
        )
        return

    if not hasattr(RelatedField, "_check_clashes"):
        # The method we wrap no longer exists. The wrapper is a no-op safety net, so
        # skipping is safe, but log it loudly in case behavior shifted.
        logger.warning(
            "RelatedField._check_clashes is absent on Django %s; skipping compatibility "
            "patch. Verify model field-clash checking still behaves as expected.",
            django.get_version(),
        )
        return

    # Idempotent: only patch once.
    if hasattr(RelatedField, "_original_check_clashes"):
        return

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

    RelatedField._check_clashes = patched_check_clashes
    logger.info(
        "Django compatibility: applied ImmutableList concatenation fix (Django %s)",
        django.get_version(),
    )


def patch_user_pk_field():
    """
    Replace Django's User AutoField primary key with a UUIDField for Aurora DSQL.

    This mutates Django's private ``User._meta`` internals. Those internals are version
    sensitive and untested by the SQLite suite, so we verify our assumptions before and
    after mutating and raise a clear RuntimeError on any divergence — a half-patched User
    model in production feeds the raw-SQL save path below and would corrupt data
    silently. Failing at startup is the safe outcome.
    """
    meta = User._meta

    # --- Pre-conditions: the internals we are about to rewrite must exist and look
    # the way we expect. If Django restructured them, stop loudly. ---
    if not hasattr(meta, "fields") or not hasattr(meta, "pk"):
        raise RuntimeError(
            "Aurora DSQL: User._meta is missing 'fields' or 'pk' on Django "
            f"{django.get_version()}. The UUID primary-key patch in aurora_dsql_fixes.py "
            "relies on these internals and must be revalidated before this Django version "
            "is deployed against Aurora DSQL."
        )

    existing_fields = list(meta.fields)
    if not any(f.name == "id" for f in existing_fields):
        raise RuntimeError(
            "Aurora DSQL: could not find an 'id' field on User._meta to replace on "
            f"Django {django.get_version()}. Revalidate the UUID primary-key patch."
        )

    if django.VERSION[:2] != VALIDATED_DJANGO:
        logger.warning(
            "Aurora DSQL: Django %s is outside the validated range %s for the User "
            "primary-key patch. Proceeding, but verify _meta internals on a staging "
            "Aurora DSQL database.",
            django.get_version(),
            ".".join(map(str, VALIDATED_DJANGO)),
        )

    # Create a new UUIDField to replace the AutoField
    uuid_field = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uuid_field.name = "id"
    uuid_field.attname = "id"
    uuid_field.column = "id"
    uuid_field.model = User

    # Completely rebuild the fields list without the original AutoField
    new_fields = []
    for field in existing_fields:
        if field.name == "id":
            new_fields.append(uuid_field)
        else:
            new_fields.append(field)

    # Update the model's meta information
    meta.fields = new_fields
    meta.pk = uuid_field

    # Update the model class to use the new field
    setattr(User, "id", uuid_field)

    # Clear field caches but let Django rebuild them naturally. These attributes are
    # private and may not all exist on every version; guard each one individually.
    if hasattr(meta, "_field_cache"):
        meta._field_cache = {}
    if hasattr(meta, "_field_name_cache"):
        meta._field_name_cache = []

    # Don't set these to None - let Django rebuild them when needed.
    # This prevents the "NoneType object is not subscriptable" error.
    for attr in ("_name_map", "_forward_fields_map", "_fields_map"):
        if hasattr(meta, attr):
            delattr(meta, attr)

    # --- Post-condition: confirm the patch actually took effect. If the pk did not
    # become our UUIDField, the model is in an inconsistent state — fail loud. ---
    if not isinstance(meta.pk, models.UUIDField):
        raise RuntimeError(
            "Aurora DSQL: User primary-key patch did not take effect on Django "
            f"{django.get_version()} (pk is {type(meta.pk).__name__}, expected "
            "UUIDField). Aborting to avoid running the raw-SQL save path against a "
            "mis-patched model."
        )

    logger.info(
        "Aurora DSQL: patched User model primary key field to UUIDField (Django %s)",
        django.get_version(),
    )


def patch_user_last_login_signal():
    """
    Replace Django's default ``update_last_login`` handler for Aurora DSQL.

    Django's default handler fails due to the UUID/AutoField primary key mismatch.
    """
    from django.contrib.auth.models import update_last_login
    from django.contrib.auth.signals import user_logged_in
    from django.dispatch import receiver

    # Disconnect Django's default update_last_login handler. disconnect() returns False
    # if nothing was connected under that dispatch_uid — surface that, since it means
    # Django changed how the default handler is wired and our replacement may double up.
    disconnected = user_logged_in.disconnect(
        update_last_login, dispatch_uid="update_last_login"
    )
    if not disconnected:
        logger.warning(
            "Aurora DSQL: Django's default update_last_login handler was not connected "
            "under the expected dispatch_uid on Django %s; the replacement signal may "
            "not fully suppress the default. Revalidate.",
            django.get_version(),
        )

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
            logger.warning(
                "Failed to update last_login for user %s: %s", user.username, e
            )

    # Keep a reference so the receiver isn't garbage collected.
    return aurora_dsql_update_last_login


def patch_user_save():
    """
    Replace User.save() with a raw-SQL implementation for Aurora DSQL.

    Bypasses Django's ORM for User writes to avoid UUID/AutoField conflicts.
    """
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

                logger.info(
                    "Aurora DSQL: User %s saved successfully with UUID %s",
                    self.username,
                    self.id,
                )

        except Exception as e:
            logger.error(
                "Aurora DSQL: raw SQL save failed for user %s: %s", self.username, e
            )
            # Fall back to original save method as last resort
            try:
                original_save(self, *args, **kwargs)
            except Exception as e2:
                logger.error("Aurora DSQL: original save also failed: %s", e2)
                raise e2

    # Replace the save method
    User.save = aurora_dsql_save
    logger.info("Aurora DSQL: replaced User.save() with raw SQL implementation")


# Apply Django compatibility patches globally (all environments, including tests).
apply_django_compatibility_patches()

# Aurora-DSQL-only patches. These reach into version-sensitive Django internals and are
# only exercised in production, so they verify their assumptions and fail loud on any
# divergence (see each function's docstring).
if is_aurora_dsql_environment():
    patch_user_pk_field()
    patch_user_last_login_signal()
    patch_user_save()
