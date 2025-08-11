"""
Management command to consolidate Django auth and contenttypes migrations for Aurora DSQL compatibility.

This command creates consolidated migrations that replace individual migrations with
ALTER COLUMN operations that are not supported by Aurora DSQL.
"""

import os
import shutil

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Consolidate Django auth and contenttypes migrations for Aurora DSQL compatibility"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the consolidated migrations (default is dry-run)",
        )
        parser.add_argument(
            "--backup",
            action="store_true",
            help="Create backup of original migrations",
        )
        parser.add_argument(
            "--apps",
            nargs="+",
            default=["auth", "contenttypes"],
            help="Apps to consolidate (default: auth contenttypes)",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                "Starting Django migration consolidation for Aurora DSQL..."
            )
        )

        # Get Django installation path
        import django

        django_path = os.path.dirname(django.__file__)

        for app_name in options["apps"]:
            self.consolidate_app_migrations(django_path, app_name, options)

        self.stdout.write(self.style.SUCCESS("\nConsolidation complete!"))
        self.stdout.write("Next steps:")
        self.stdout.write(
            "1. Run: python manage.py migrate --fake <app> 0001 (if tables already exist)"
        )
        self.stdout.write(
            "2. Run: python manage.py migrate (to apply any remaining migrations)"
        )

        # Automatically fix ContentType cache issues after consolidation
        if options["apply"]:
            self.stdout.write(
                "\n=== Fixing ContentType cache for UUID compatibility ==="
            )
            try:
                # Only try to fix cache if tables exist
                if self.tables_exist():
                    from django.core.management import call_command

                    call_command("fix_contenttype_cache", verbosity=1)
                    self.stdout.write(
                        self.style.SUCCESS("ContentType cache fixed automatically!")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "Database tables don't exist yet - skipping cache fix"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING("Could not fix ContentType cache: {}".format(e))
                )
                self.stdout.write(
                    "You may need to run: python manage.py fix_contenttype_cache"
                )

    def consolidate_app_migrations(self, django_path, app_name, options):
        self.stdout.write(f"\n=== Processing {app_name} app ===")

        migrations_path = os.path.join(django_path, "contrib", app_name, "migrations")

        if not os.path.exists(migrations_path):
            self.stdout.write(
                self.style.ERROR(
                    f"Django {app_name} migrations not found at: {migrations_path}"
                )
            )
            return

        self.stdout.write(f"Found Django {app_name} migrations at: {migrations_path}")

        # List current migrations
        migration_files = [
            f
            for f in os.listdir(migrations_path)
            if f.endswith(".py") and f != "__init__.py"
        ]
        self.stdout.write(f"Found {len(migration_files)} migration files:")
        for f in sorted(migration_files):
            self.stdout.write(f"  - {f}")

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN MODE - No changes will be made to {app_name}"
                )
            )
            return

        # Create backup if requested
        if options["backup"]:
            backup_path = migrations_path + "_backup"
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.copytree(migrations_path, backup_path)
            self.stdout.write(f"Created backup at: {backup_path}")

        # Get consolidated migration content
        if app_name == "contenttypes":
            consolidated_migration = self.get_consolidated_contenttypes_migration()
        elif app_name == "auth":
            consolidated_migration = self.get_consolidated_auth_migration()
        else:
            self.stdout.write(
                self.style.ERROR(f"No consolidated migration available for {app_name}")
            )
            return

        # Remove old migration files (except __init__.py)
        for f in migration_files:
            file_path = os.path.join(migrations_path, f)
            os.remove(file_path)
            self.stdout.write(f"Removed: {f}")

        # Create new consolidated migration
        consolidated_path = os.path.join(migrations_path, "0001_initial.py")
        with open(consolidated_path, "w") as f:
            f.write(consolidated_migration)

        self.stdout.write(
            self.style.SUCCESS("Created consolidated migration: 0001_initial.py")
        )

        # Check migration state in database
        self.check_migration_state(app_name)

    def get_consolidated_contenttypes_migration(self):
        """
        Generate consolidated contenttypes migration with environment-aware field types.
        """
        # Check if we're using Aurora DSQL
        is_aurora_dsql = self.is_aurora_dsql_environment()

        if is_aurora_dsql:
            # Aurora DSQL version with UUID primary keys
            return '''# Generated by consolidate_django_migrations for Aurora DSQL compatibility
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContentType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, auto_created=True)),
                ('app_label', models.CharField(max_length=100)),
                ('model', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=100, null=True, blank=True)),  # Retained for compatibility
            ],
            options={
                'verbose_name': 'content type',
                'verbose_name_plural': 'content types',
                'db_table': 'django_content_type',
            },
        ),
        # Custom operation to ensure UUID primary key compatibility
        migrations.RunSQL(
            sql=[
                # Ensure the ContentType table ID column uses UUID with proper default
                "ALTER TABLE django_content_type ALTER COLUMN id SET DEFAULT gen_random_uuid();",
            ],
            reverse_sql=[
                "ALTER TABLE django_content_type ALTER COLUMN id DROP DEFAULT;",
            ],
        ),
        migrations.AlterUniqueTogether(
            name='contenttype',
            unique_together={('app_label', 'model')},
        ),
        # Data migration to populate the name field
        migrations.RunPython(
            code=lambda apps, schema_editor: populate_contenttype_names(apps, schema_editor),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def populate_contenttype_names(apps, schema_editor):
    """Populate the name field with model names for compatibility."""
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for ct in ContentType.objects.all():
        if not ct.name:
            ct.name = ct.model
            ct.save()
'''
        else:
            # Standard Django version with integer primary keys for development
            return '''# Generated by consolidate_django_migrations for development compatibility
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContentType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_label', models.CharField(max_length=100)),
                ('model', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=100, null=True, blank=True)),  # Retained for compatibility
            ],
            options={
                'verbose_name': 'content type',
                'verbose_name_plural': 'content types',
                'db_table': 'django_content_type',
            },
        ),
        migrations.AlterUniqueTogether(
            name='contenttype',
            unique_together={('app_label', 'model')},
        ),
        # Data migration to populate the name field
        migrations.RunPython(
            code=lambda apps, schema_editor: populate_contenttype_names(apps, schema_editor),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def populate_contenttype_names(apps, schema_editor):
    """Populate the name field with model names for compatibility."""
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for ct in ContentType.objects.all():
        if not ct.name:
            ct.name = ct.model
            ct.save()
'''

    def get_consolidated_auth_migration(self):
        """
        Generate consolidated auth migration with environment-aware field types.
        """
        # Check if we're using Aurora DSQL
        is_aurora_dsql = self.is_aurora_dsql_environment()

        if is_aurora_dsql:
            # Aurora DSQL version with UUID primary keys
            return """# Generated by consolidate_django_migrations for Aurora DSQL compatibility
from django.db import migrations, models
import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='content type')),
                ('codename', models.CharField(max_length=100, verbose_name='codename')),
            ],
            options={
                'verbose_name': 'permission',
                'verbose_name_plural': 'permissions',
                'db_table': 'auth_permission',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='name')),
                ('permissions', models.ManyToManyField(blank=True, to='auth.permission', verbose_name='permissions')),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
                'db_table': 'auth_group',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, auto_created=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'db_table': 'auth_user',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        # Custom operation to ensure UUID primary key compatibility
        migrations.RunSQL(
            sql=[
                # Ensure the User table ID column uses UUID with proper default
                "ALTER TABLE auth_user ALTER COLUMN id SET DEFAULT gen_random_uuid();",
                "ALTER TABLE auth_permission ALTER COLUMN id SET DEFAULT gen_random_uuid();",
                "ALTER TABLE auth_group ALTER COLUMN id SET DEFAULT gen_random_uuid();",
            ],
            reverse_sql=[
                "ALTER TABLE auth_user ALTER COLUMN id DROP DEFAULT;",
                "ALTER TABLE auth_permission ALTER COLUMN id DROP DEFAULT;",
                "ALTER TABLE auth_group ALTER COLUMN id DROP DEFAULT;",
            ],
        ),
        migrations.AlterUniqueTogether(
            name='permission',
            unique_together={('content_type', 'codename')},
        ),
    ]
"""
        else:
            # Standard Django version with integer primary keys for development
            return """# Generated by consolidate_django_migrations for development compatibility
from django.db import migrations, models
import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='content type')),
                ('codename', models.CharField(max_length=100, verbose_name='codename')),
            ],
            options={
                'verbose_name': 'permission',
                'verbose_name_plural': 'permissions',
                'db_table': 'auth_permission',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='name')),
                ('permissions', models.ManyToManyField(blank=True, to='auth.permission', verbose_name='permissions')),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
                'db_table': 'auth_group',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'db_table': 'auth_user',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='permission',
            unique_together={('content_type', 'codename')},
        ),
    ]
"""

    def is_aurora_dsql_environment(self):
        """
        Check if we're running in an Aurora DSQL environment.
        """
        try:
            from django.db import connection

            db_engine = connection.settings_dict.get("ENGINE", "")
            return "aurora" in db_engine.lower() or "dsql" in db_engine.lower()
        except (ImportError, AttributeError, KeyError):
            return False

    def check_migration_state(self, app_name):
        """Check and report on migration state in database."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM django_migrations
                    WHERE app = %s
                """,
                    [app_name],
                )
                migration_count = cursor.fetchone()[0]

                if migration_count > 0:
                    self.stdout.write(
                        f"Found {migration_count} existing {app_name} migration records"
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"You may need to run: python manage.py migrate --fake {app_name} 0001"
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not check migration state for {app_name}: {e}"
                )
            )

    def tables_exist(self):
        """Check if tables exist in the database."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name IN ('auth_user', 'auth_group', 'auth_permission', 'django_content_type')
                """
                )
                table_count = cursor.fetchone()[0]

                return table_count > 0

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not check table existence: {e}")
            )
            return False
