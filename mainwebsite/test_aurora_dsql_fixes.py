"""
Unit tests for mainwebsite.aurora_dsql_fixes.

These cover the Aurora-DSQL-only compatibility patches that the rest of the suite
never exercises: the SQLite test database makes is_aurora_dsql_environment() return
False, so the User._meta monkeypatching, fail-loud guards, and raw-SQL paths are
otherwise untested. These tests drive that code directly (with a stand-in User) so a
future Django upgrade that restructures the patched internals is caught here rather
than silently in production.
"""

from types import SimpleNamespace
from unittest.mock import patch

import django
from django.db import models
from django.test import SimpleTestCase

import mainwebsite.aurora_dsql_fixes as fx


def _field(name):
    """Minimal stand-in for a Django model field (only .name is read)."""
    return SimpleNamespace(name=name)


class IsAuroraDsqlEnvironmentTests(SimpleTestCase):
    @patch("mainwebsite.aurora_dsql_fixes.connection")
    def test_detects_aurora_engine(self, mock_connection):
        mock_connection.settings_dict = {"ENGINE": "aurora_dsql_django"}
        self.assertTrue(fx.is_aurora_dsql_environment())

    @patch("mainwebsite.aurora_dsql_fixes.connection")
    def test_detects_dsql_substring(self, mock_connection):
        mock_connection.settings_dict = {"ENGINE": "some.custom.dsql.backend"}
        self.assertTrue(fx.is_aurora_dsql_environment())

    @patch("mainwebsite.aurora_dsql_fixes.connection")
    def test_sqlite_is_not_aurora(self, mock_connection):
        mock_connection.settings_dict = {"ENGINE": "django.db.backends.sqlite3"}
        self.assertFalse(fx.is_aurora_dsql_environment())

    @patch("mainwebsite.aurora_dsql_fixes.connection")
    def test_returns_false_on_error(self, mock_connection):
        # A broken/unconfigured connection must not raise during startup.
        mock_connection.settings_dict.get.side_effect = RuntimeError("no connection")
        self.assertFalse(fx.is_aurora_dsql_environment())


class ApplyCompatibilityPatchTests(SimpleTestCase):
    def test_check_clashes_patch_applied_and_idempotent(self):
        from django.db.models.fields.related import RelatedField

        # The module applied the patch at import time.
        self.assertTrue(hasattr(RelatedField, "_original_check_clashes"))
        patched = RelatedField._check_clashes

        # Calling again must be a no-op (must not re-wrap the already-wrapped method).
        fx.apply_django_compatibility_patches()
        self.assertIs(RelatedField._check_clashes, patched)
        self.assertIsNot(
            RelatedField._check_clashes, RelatedField._original_check_clashes
        )


class PatchUserPkFieldGuardTests(SimpleTestCase):
    """The fail-loud pre/post conditions that protect against Django internal drift."""

    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_raises_when_meta_missing_fields(self, mock_user):
        mock_user._meta = SimpleNamespace(pk=_field("id"))  # no `fields`
        with self.assertRaises(RuntimeError):
            fx.patch_user_pk_field()

    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_raises_when_meta_missing_pk(self, mock_user):
        mock_user._meta = SimpleNamespace(fields=[_field("id")])  # no `pk`
        with self.assertRaises(RuntimeError):
            fx.patch_user_pk_field()

    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_raises_when_no_id_field(self, mock_user):
        mock_user._meta = SimpleNamespace(
            fields=[_field("username"), _field("email")], pk=_field("username")
        )
        with self.assertRaises(RuntimeError):
            fx.patch_user_pk_field()

    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_happy_path_replaces_pk_with_uuid_field(self, mock_user):
        meta = SimpleNamespace(
            fields=[_field("id"), _field("username"), _field("email")],
            pk=_field("id"),
        )
        mock_user._meta = meta

        fx.patch_user_pk_field()

        # Post-condition: the AutoField id has become a UUIDField primary key.
        self.assertIsInstance(meta.pk, models.UUIDField)
        self.assertTrue(meta.pk.primary_key)
        id_fields = [f for f in meta.fields if f.name == "id"]
        self.assertEqual(len(id_fields), 1)
        self.assertIsInstance(id_fields[0], models.UUIDField)
        # Non-id fields are preserved and order is maintained.
        self.assertEqual([f.name for f in meta.fields], ["id", "username", "email"])

    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_invalidates_forward_fields_map_cache(self, mock_user):
        # A stale cached forward-field map must be dropped so it is rebuilt lazily
        # rather than left pointing at the pre-patch field objects.
        meta = SimpleNamespace(
            fields=[_field("id"), _field("username")], pk=_field("id")
        )
        meta._forward_fields_map = {"id": _field("id")}  # stale cache
        mock_user._meta = meta

        fx.patch_user_pk_field()

        self.assertNotIn("_forward_fields_map", meta.__dict__)

    @patch("mainwebsite.aurora_dsql_fixes.logger")
    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_warns_when_outside_validated_django_range(self, mock_user, mock_logger):
        mock_user._meta = SimpleNamespace(fields=[_field("id")], pk=_field("id"))
        with patch.object(fx, "VALIDATED_DJANGO", {(99, 99)}):
            fx.patch_user_pk_field()
        self.assertTrue(
            mock_logger.warning.called,
            "expected a loud warning when running outside the validated Django range",
        )

    @patch("mainwebsite.aurora_dsql_fixes.logger")
    @patch("mainwebsite.aurora_dsql_fixes.User")
    def test_no_warning_when_inside_validated_range(self, mock_user, mock_logger):
        mock_user._meta = SimpleNamespace(fields=[_field("id")], pk=_field("id"))
        with patch.object(fx, "VALIDATED_DJANGO", {django.VERSION[:2]}):
            fx.patch_user_pk_field()
        self.assertFalse(mock_logger.warning.called)
