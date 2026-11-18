from django.core.management.base import BaseCommand
from apps.settings.seeding import seed_all_platform_data


class Command(BaseCommand):
    help = "Seeds initial localization, RBAC, multi-tenant agencies, properties, CRM, deals, and accounting data."

    def handle(self, *args, **options):
        seed_all_platform_data(log_fn=self.stdout.write, verify_all=True)
        self.stdout.write(self.style.SUCCESS("Bootstrap completed successfully."))
