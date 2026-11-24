from pathlib import Path
from django.core.management.base import BaseCommand
from apps.settings.management.commands.seed_all import _export_postgresql_seed_sql
from apps.settings.seeding import seed_all_platform_data
from common.tenant.context import tenant_bypass


class Command(BaseCommand):
    help = "Idempotently seeds realistic demo data for non-production environments across all PostgreSQL tables and all 9 roles."

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Suppress verbose logs.")
        parser.add_argument(
            "--export-sql",
            type=str,
            default="",
            help="Optional path to export idempotent PostgreSQL INSERT script.",
        )

    def handle(self, *args, **options):
        quiet = options.get("quiet", False)
        export_sql = (options.get("export_sql") or "").strip()

        with tenant_bypass(reason="platform_seed"):
            res = seed_all_platform_data(
                log_fn=None if quiet else self.stdout.write,
                verify_all=True,
            )
        if export_sql:
            written = _export_postgresql_seed_sql(Path(export_sql))
            if not quiet:
                self.stdout.write(
                    self.style.SUCCESS(f"Exported {written} PostgreSQL INSERT statements to {export_sql}.")
                )
        if not quiet:
            self.stdout.write(
                self.style.SUCCESS(
                    f"seed_demo completed: {len(res['counts'])} domain tables verified non-empty."
                )
            )
