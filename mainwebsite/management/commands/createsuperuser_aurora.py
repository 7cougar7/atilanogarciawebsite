"""
Aurora DSQL-specific createsuperuser command.

This command handles the UUID primary key mismatch between Django's User model
and the consolidated migration schema in Aurora DSQL environments.
"""

import uuid

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Create a superuser with Aurora DSQL UUID compatibility"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            help="Specifies the login for the superuser.",
        )
        parser.add_argument(
            "--email",
            help="Specifies the email for the superuser.",
        )
        parser.add_argument(
            "--password",
            help="Specifies the password for the superuser.",
        )

    def is_aurora_dsql_environment(self):
        """Check if we're running in an Aurora DSQL environment."""
        db_engine = connection.settings_dict.get("ENGINE", "")
        return "aurora" in db_engine.lower() or "dsql" in db_engine.lower()

    def handle(self, *args, **options):
        """
        Handle superuser creation with UUID compatibility for Aurora DSQL.
        """
        if not self.is_aurora_dsql_environment():
            self.stdout.write(
                self.style.WARNING(
                    "Not an Aurora DSQL environment. Use 'python manage.py createsuperuser' instead."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Aurora DSQL detected - using UUID-compatible superuser creation"
            )
        )

        try:
            # Get user input
            username = options.get("username")
            if not username:
                username = input("Username: ")

            email = options.get("email")
            if not email:
                email = input("Email address: ")

            # Validate email format
            from django.core.exceptions import ValidationError
            from django.core.validators import validate_email

            try:
                validate_email(email)
            except ValidationError:
                raise CommandError("Enter a valid email address.")

            password = options.get("password")
            if not password:
                import getpass

                password = getpass.getpass("Password: ")
                password2 = getpass.getpass("Password (again): ")
                if password != password2:
                    raise CommandError("Passwords don't match")

            # Check if user already exists
            if User.objects.filter(username=username).exists():
                raise CommandError(f"User '{username}' already exists.")

            # Create superuser with explicit UUID
            with transaction.atomic():
                # Generate UUID for the user
                user_id = uuid.uuid4()

                # Hash the password
                hashed_password = make_password(password)

                # Use raw SQL to insert the user with UUID primary key
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO auth_user (
                            id, password, last_login, is_superuser, username,
                            first_name, last_name, email, is_staff, is_active, date_joined
                        ) VALUES (
                            %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                    """,
                        [
                            str(user_id),
                            hashed_password,
                            True,  # is_superuser
                            username,
                            "",  # first_name
                            "",  # last_name
                            email,
                            True,  # is_staff
                            True,  # is_active
                        ],
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Superuser "{username}" created successfully with UUID: {user_id}'
                    )
                )

        except Exception as e:
            raise CommandError(f"Error creating superuser: {e}")
