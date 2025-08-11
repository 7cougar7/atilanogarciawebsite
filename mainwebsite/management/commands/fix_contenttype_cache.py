"""
Management command to fix Django ContentType cache issues with UUID primary keys.

This command resolves the UUID/numeric comparison errors that occur when Django's
ContentType system tries to use cached numeric IDs with UUID-based database schemas.
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Fix Django ContentType cache issues with UUID primary keys"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force cache clearing even if not using Aurora DSQL",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Fixing ContentType cache for UUID compatibility...")
        )

        # Check if we're using Aurora DSQL
        db_engine = connection.settings_dict.get("ENGINE", "")
        if (
            not options["force"]
            and "aurora" not in db_engine.lower()
            and "dsql" not in db_engine.lower()
        ):
            self.stdout.write(
                self.style.WARNING("Not using Aurora DSQL - skipping cache fix")
            )
            return

        try:
            with transaction.atomic():
                self.fix_contenttype_cache()
                self.verify_uuid_compatibility()

            self.stdout.write(
                self.style.SUCCESS("ContentType cache fixed successfully!")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fixing ContentType cache: {e}"))
            raise

    def fix_contenttype_cache(self):
        """
        Fix Django's ContentType cache to work with UUID primary keys.
        """
        self.stdout.write("Clearing ContentType cache...")

        # Clear all ContentType caches
        ContentType.objects.clear_cache()

        # Force Django to reload ContentType data from database
        # This ensures it uses the correct UUID values
        self.stdout.write("Reloading ContentType data with UUID values...")

        # Get all ContentTypes to populate cache with correct UUID values
        content_types = list(ContentType.objects.all())
        self.stdout.write(
            f"Loaded {len(content_types)} ContentTypes with UUID primary keys"
        )

        # Verify that all ContentTypes have UUID primary keys
        for ct in content_types:
            if not isinstance(ct.pk, str) and not hasattr(ct.pk, "hex"):
                self.stdout.write(
                    self.style.WARNING(
                        f"ContentType {ct} has non-UUID primary key: {ct.pk} ({type(ct.pk)})"
                    )
                )

    def verify_uuid_compatibility(self):
        """
        Verify that Permission queries work correctly with UUID ContentTypes.
        """
        self.stdout.write("Verifying UUID compatibility...")

        try:
            # Test a simple Permission query that was failing before
            user_ct = ContentType.objects.get(app_label="auth", model="user")
            self.stdout.write(
                f"User ContentType ID: {user_ct.id} (type: {type(user_ct.id)})"
            )

            # This query was failing with "operator does not exist: uuid = numeric"
            # Now it should work with proper UUID handling
            perm_count = Permission.objects.filter(content_type=user_ct).count()
            self.stdout.write(f"Found {perm_count} permissions for User ContentType")

            # Test direct ID query
            perm_count_by_id = Permission.objects.filter(
                content_type_id=user_ct.id
            ).count()
            self.stdout.write(
                f"Found {perm_count_by_id} permissions by content_type_id"
            )

            if perm_count != perm_count_by_id:
                raise ValueError(
                    f"Permission count mismatch: {perm_count} vs {perm_count_by_id}"
                )

            self.stdout.write(self.style.SUCCESS("UUID compatibility verified!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"UUID compatibility check failed: {e}"))

            # Try to diagnose the issue
            self.diagnose_uuid_issue()
            raise

    def diagnose_uuid_issue(self):
        """
        Diagnose UUID/numeric comparison issues.
        """
        self.stdout.write("Diagnosing UUID/numeric comparison issue...")

        with connection.cursor() as cursor:
            # Check actual database schema
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'auth_permission' AND column_name = 'content_type_id'
            """
            )
            result = cursor.fetchone()
            if result:
                self.stdout.write(f"auth_permission.content_type_id type: {result[1]}")

            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'django_content_type' AND column_name = 'id'
            """
            )
            result = cursor.fetchone()
            if result:
                self.stdout.write(f"django_content_type.id type: {result[1]}")

            # Check for any remaining numeric values in the database
            cursor.execute(
                """
                SELECT COUNT(*) FROM auth_permission
                WHERE content_type_id::text ~ '^[0-9]+$'
            """
            )
            numeric_count = cursor.fetchone()[0]
            if numeric_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Found {numeric_count} permissions with numeric content_type_id values"
                    )
                )
