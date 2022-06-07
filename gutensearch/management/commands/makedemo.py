from django.contrib.auth.models import User
from django.core import management
from django.core.management.base import BaseCommand
from django.db import transaction

from django_search_example.settings import DEMO_PASSWORD


class Command(BaseCommand):
    help = "Make database with demo data"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self._create_demo_admin_if_not_exists()
        self._create_demo_documents()

    def _create_demo_admin_if_not_exists(self, username: str = "admin"):
        with transaction.atomic():
            result = User.objects.select_for_update().filter(username=username).first()
            if result is None:
                self.stdout.write(f"Adding demo admin {username!r}")
                User.objects.create_superuser(username, password=DEMO_PASSWORD)

    def _create_demo_documents(self, count: int = 10):
        management.call_command("gutenlader", max_count=count)
