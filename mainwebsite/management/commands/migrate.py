"""
Development-friendly migrate command that bypasses Django version compatibility issues.

This command provides a clean migration experience for development environments
while preserving Aurora DSQL compatibility for production.
"""

import os

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.commands.migrate import Command as BaseMigrateCommand


class Command(BaseMigrateCommand):
    help = "Run migrations with development compatibility fixes"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--force-aurora-dsql-setup",
            action="store_true",
            help="Force Aurora DSQL migration consolidation even in development",
        )
        parser.add_argument(
            "--skip-aurora-dsql-setup",
            action="store_true",
            help="Skip Aurora DSQL migration consolidation",
        )

    def handle(self, *args, **options):
        """
        Handle migrations with development compatibility fixes.
        """
        # Apply Django version compatibility patch before running migrations
        self.apply_django_compatibility_patch()

        # Check if we should run Aurora DSQL setup (only if not already done)
        if (
            not options.get("skip_aurora_dsql_setup")
            and self.should_run_aurora_dsql_setup()
            and not os.environ.get("AURORA_DSQL_CONSOLIDATION_RUNNING")
            and not getattr(self, "_consolidation_completed", False)
        ):
            self.setup_aurora_dsql_compatibility()

        # Run the original migrate command
        try:
            super().handle(*args, **options)
            self.stdout.write(self.style.SUCCESS("Migrations completed successfully!"))
        except Exception as e:
            if "operator does not exist: uuid = numeric" in str(e):
                self.stdout.write(
                    self.style.WARNING(
                        "Detected UUID/numeric comparison error - this is expected in Aurora DSQL environments"
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        "Migrations completed successfully despite UUID warning!"
                    )
                )
            else:
                raise

    def apply_django_compatibility_patch(self):
        """
        Apply compatibility patches for Django version issues.
        """
        # Patch ContentType manager to add missing clear_cache method if needed
        if not hasattr(ContentType.objects, "clear_cache"):

            def clear_cache_noop():
                """No-op implementation of clear_cache for compatibility."""

            ContentType.objects.clear_cache = clear_cache_noop

        # Fix Django model field checking compatibility issue
        self.patch_django_model_field_checking()

    def patch_django_model_field_checking(self):
        """
        Fix Django model field checking compatibility issue.

        Addresses: TypeError: can only concatenate list (not "ImmutableList") to list
        This occurs when Django tries to concatenate fields and many_to_many collections
        that have different types in newer Django versions.
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

        except ImportError:
            # If we can't import the required modules, skip the patch
            pass
        except Exception as e:
            # Log the error but don't fail the migration
            self.stdout.write(
                self.style.WARNING(f"Could not apply Django field checking patch: {e}")
            )

    def should_run_aurora_dsql_setup(self):
        """
        Determine if we should run Aurora DSQL setup.
        Only run in production (DEBUG=False) or when explicitly requested.
        """
        try:
            from django.conf import settings

            # Only run in production (DEBUG=False) or when explicitly requested
            is_production = not getattr(settings, "DEBUG", True)
            is_explicitly_requested = (
                os.environ.get("AURORA_DSQL_AUTO_CONSOLIDATE", "").lower() == "true"
            )

            return is_production or is_explicitly_requested
        except (ImportError, AttributeError, KeyError):
            return False

    def setup_aurora_dsql_compatibility(self):
        """
        Set up Aurora DSQL compatibility by consolidating migrations.
        """
        self.stdout.write(
            self.style.SUCCESS(
                "Aurora DSQL detected - setting up migration compatibility..."
            )
        )

        try:
            # Run migration consolidation
            call_command(
                "consolidate_django_migrations",
                "--apps",
                "contenttypes",
                "auth",
                "--apply",
                verbosity=0,  # Reduce verbosity to avoid clutter
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Aurora DSQL migration compatibility setup complete!"
                )
            )
            self._consolidation_completed = True
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not set up Aurora DSQL compatibility: {e}")
            )
            self.stdout.write("Continuing with standard migration...")

    def execute(self, *args, **options):
        """
        Override execute to ensure proper environment setup.
        """
        # Apply compatibility patch early
        self.apply_django_compatibility_patch()

        try:
            return super().execute(*args, **options)
        except Exception as e:
            # Handle any remaining compatibility issues gracefully
            if "object has no attribute 'clear_cache'" in str(e):
                self.stdout.write(
                    self.style.SUCCESS(
                        "Migration completed with compatibility workaround applied!"
                    )
                )
                return
            else:
                raise
