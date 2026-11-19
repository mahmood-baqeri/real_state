from django.core.management.base import BaseCommand, CommandError
from apps.settings.seeding import clear_demo_platform_data


class Command(BaseCommand):
    help = "Safely deletes seeded demo records only in non-production environments (--confirm required)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required confirmation flag to remove seeded demo records.",
        )

    def handle(self, *args, **options):
        if not options.get("confirm"):
            raise CommandError("برای حذف داده‌های آزمایشی باید فلگ --confirm ارسال شود.")
        removed = clear_demo_platform_data(log_fn=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"Demo data cleared: {removed}"))
