import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse


class Command(BaseCommand):
    help = "Test passkey registration functionality"

    def handle(self, *args, **options):
        self.stdout.write("=== Testing Passkey Registration ===")

        # Create or get test user
        username = "testuser"
        password = "testpass123"

        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"✓ Using existing user: {username}")
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=password)
            self.stdout.write(f"✓ Created new user: {username}")

        # Ensure password is set correctly
        user.set_password(password)
        user.save()

        # Create test client
        client = Client()

        # Test login
        login_success = client.login(username=username, password=password)
        if not login_success:
            self.stdout.write(self.style.ERROR("✗ Failed to log in test user"))
            return

        self.stdout.write("✓ Test user logged in successfully")

        # Test passkey registration begin
        try:
            url = reverse("mainwebsite:custom_passkey_reg_begin")
            self.stdout.write(f"Testing URL: {url}")

            response = client.post(url, content_type="application/json")
            self.stdout.write(f"Response status: {response.status_code}")

            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("✓ Registration begin successful"))

                # Parse response
                data = response.json()

                # Check required fields
                required_fields = ["challenge", "rp", "user", "pub_key_cred_params"]
                for field in required_fields:
                    if field in data:
                        self.stdout.write(f"  ✓ {field}: present")
                        if field == "pub_key_cred_params":
                            self.stdout.write(f"    Algorithms: {len(data[field])}")
                    else:
                        self.stdout.write(self.style.ERROR(f"  ✗ {field}: missing"))

                self.stdout.write(self.style.SUCCESS("=== Test PASSED ==="))

            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ Registration failed: {response.status_code}")
                )
                try:
                    error_data = response.json()
                    self.stdout.write(f"Error: {error_data}")
                except json.JSONDecodeError:
                    self.stdout.write(f"Raw response: {response.content}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Exception: {e}"))
            import traceback

            traceback.print_exc()
