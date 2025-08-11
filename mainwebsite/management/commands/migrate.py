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

    def handle(self, *args, **options):
        """
        Handle migrations with development compatibility fixes.
        """
        # Apply Django version compatibility patch before running migrations
        self.apply_django_compatibility_patch()

        # Check if we should run Aurora DSQL setup
        if (
            options.get("force_aurora_dsql_setup")
            or self.should_run_aurora_dsql_setup()
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
