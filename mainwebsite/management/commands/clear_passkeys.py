from django.core.management.base import BaseCommand
from passkeys.models import UserPasskey


class Command(BaseCommand):
    help = "Deletes all passkeys from the database."

    def handle(self, *args, **options):
        count, _ = UserPasskey.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {count} passkeys."))
