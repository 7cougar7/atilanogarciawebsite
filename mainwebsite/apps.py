import os

from django.apps import AppConfig
from django.db.models.signals import pre_migrate


class MainwebsiteConfig(AppConfig):
    name = "mainwebsite"
    default_auto_field = "django.db.models.BigAutoField"

    # Class variable to track consolidation state
    _consolidation_completed = False

    def ready(self):
        """
        Called when Django starts up. Set up automatic migration consolidation
        for Aurora DSQL compatibility.
        """
        # Only run consolidation in production or when explicitly requested
        if self.should_run_consolidation():
            self.setup_automatic_consolidation()

    def should_run_consolidation(self):
        """
        Determine if we should run automatic consolidation.
        Run in production (DEBUG=False) or when AURORA_DSQL_AUTO_CONSOLIDATE=True
        """
        from django.conf import settings

        # Always run if explicitly requested
        if os.environ.get("AURORA_DSQL_AUTO_CONSOLIDATE", "").lower() == "true":
            return True

        # Run in production (when DEBUG=False and using Aurora DSQL)
        if not getattr(settings, "DEBUG", True):
            db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
            return "aurora" in db_engine.lower() or "dsql" in db_engine.lower()

        return False

    def setup_automatic_consolidation(self):
        """
        Set up automatic migration consolidation before migrations run.
        """
        # Connect to pre_migrate signal to run consolidation
        pre_migrate.connect(
            self.auto_consolidate_migrations,
            dispatch_uid="aurora_dsql_auto_consolidate",
        )

    def auto_consolidate_migrations(self, sender, **kwargs):
        """
        Automatically consolidate Django auth and contenttypes migrations
        for Aurora DSQL compatibility before migrations run.
        """
        # Prevent multiple consolidations in the same process
        if MainwebsiteConfig._consolidation_completed:
            return

        # Skip if consolidation is already running (prevent recursion)
        if os.environ.get("AURORA_DSQL_CONSOLIDATION_RUNNING") == "true":
            return

        import logging

        from django.core.management import call_command
        from django.db import connection

        logger = logging.getLogger(__name__)

        try:
            # Check if we're using Aurora DSQL
            db_engine = connection.settings_dict.get("ENGINE", "")
            if "aurora" not in db_engine.lower() and "dsql" not in db_engine.lower():
                return

            logger.info(
                "Aurora DSQL detected - running automatic migration consolidation"
            )

            # Set flag to prevent recursion
            os.environ["AURORA_DSQL_CONSOLIDATION_RUNNING"] = "true"

            # Run the consolidation command
            call_command(
                "consolidate_django_migrations",
                "--apps",
                "contenttypes",
                "auth",
                "--apply",
                verbosity=1,
            )

            # Mark consolidation as completed
            MainwebsiteConfig._consolidation_completed = True

            logger.info("Migration consolidation completed successfully")

        except Exception as e:
            logger.warning(f"Could not run automatic migration consolidation: {e}")
            # Don't fail the migration process if consolidation fails
        finally:
            # Clean up the flag
            os.environ.pop("AURORA_DSQL_CONSOLIDATION_RUNNING", None)

    def clear_contenttype_cache(self):
        """
        Clear Django's ContentType cache to resolve UUID/numeric comparison issues.
        This ensures Django uses the correct UUID values from the database.
        """
        try:
            from django.contrib.contenttypes.models import ContentType

            # Clear the ContentType cache
            ContentType.objects.clear_cache()

            # Force reload of ContentType data with correct UUID types
            # This helps resolve the UUID/numeric comparison errors
            ContentType.objects.all().count()

        except Exception:
            # Ignore cache clearing errors during startup
            pass
