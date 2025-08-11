"""
Custom migrate command that automatically handles Aurora DSQL compatibility.

This command extends Django's migrate command to automatically:
1. Consolidate auth and contenttypes migrations for Aurora DSQL compatibility
2. Fix UUID/numeric comparison issues in Django's ORM
3. Ensure consistent deployment in fresh environments
"""

import os

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.commands.migrate import Command as BaseMigrateCommand
from django.db import connection


class Command(BaseMigrateCommand):
    help = "Run migrations with automatic Aurora DSQL compatibility handling"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--skip-aurora-dsql-setup",
            action="store_true",
            help="Skip automatic Aurora DSQL migration consolidation",
        )

    def handle(self, *args, **options):
        """
        Handle migrations with automatic Aurora DSQL compatibility.
        """
        # Check if we should run Aurora DSQL setup
        if (
            not options.get("skip_aurora_dsql_setup")
            and self.should_run_aurora_dsql_setup()
        ):
            self.setup_aurora_dsql_compatibility()

        # Run the original migrate command
        try:
            super().handle(*args, **options)
        except Exception as e:
            # If migration fails with UUID/numeric error, try to fix it
            if "operator does not exist: uuid = numeric" in str(e):
                self.stdout.write(
                    self.style.WARNING(
                        "Detected UUID/numeric comparison error - attempting to fix..."
                    )
                )
                self.fix_uuid_numeric_error()
                # Retry the migration
                super().handle(*args, **options)
            else:
                raise

    def should_run_aurora_dsql_setup(self):
        """
        Determine if we should run Aurora DSQL setup.
        """
        try:
            db_engine = connection.settings_dict.get("ENGINE", "")
            return "aurora" in db_engine.lower() or "dsql" in db_engine.lower()
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

    def fix_uuid_numeric_error(self):
        """
        Fix UUID/numeric comparison errors by clearing Django's internal caches
        and forcing proper UUID handling.
        """
        self.stdout.write("Fixing UUID/numeric comparison error...")

        try:
            # Clear all Django caches that might contain stale data
            self.clear_django_caches()

            # Force Django to reload ContentType data with correct UUID values
            self.reload_contenttype_data()

            self.stdout.write(self.style.SUCCESS("UUID/numeric error fix applied!"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not fix UUID error: {e}"))

    def clear_django_caches(self):
        """
        Clear Django's internal caches that might contain stale numeric IDs.
        """
        # Clear ContentType cache
        ContentType.objects.clear_cache()

        # Clear Django's app registry cache if possible
        try:
            from django.apps import apps

            apps.clear_cache()
        except (ImportError, AttributeError):
            pass

        # Force garbage collection to clear any cached objects
        import gc

        gc.collect()

    def reload_contenttype_data(self):
        """
        Force Django to reload ContentType data with correct UUID values.
        """
        # Get all ContentTypes to populate cache with correct UUID values
        content_types = list(ContentType.objects.all())

        # Force evaluation of querysets to ensure proper UUID handling
        for ct in content_types:
            # Access the primary key to ensure it's loaded correctly
            _ = ct.pk
            _ = ct.id

        self.stdout.write(
            f"Reloaded {len(content_types)} ContentTypes with UUID values"
        )

    def execute(self, *args, **options):
        """
        Override execute to ensure proper environment setup.
        """
        # Set environment variable to indicate we're using the custom migrate command
        os.environ["AURORA_DSQL_CUSTOM_MIGRATE"] = "true"

        try:
            return super().execute(*args, **options)
        finally:
            # Clean up environment variable
            os.environ.pop("AURORA_DSQL_CUSTOM_MIGRATE", None)
