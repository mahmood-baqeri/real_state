from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "Safely adopts the former cooperation/after-sales app schema under "
        "the permanent ecosystem domain name before running migrations."
    )

    TABLE_RENAMES = {
        "phase9_after_deal_case": "ecosystem_after_deal_case",
        "phase9_after_deal_update": "ecosystem_after_deal_update",
        "phase9_cooperation_property_share": "ecosystem_cooperation_property_share",
        "phase9_cooperation_settlement": "ecosystem_cooperation_settlement",
        "phase9_trust_score_snapshot": "ecosystem_trust_score_snapshot",
        "phase9_owner_report_snapshot": "ecosystem_owner_report_snapshot",
    }

    MIGRATION_RENAMES = {
        "0001_initial": "0001_initial",
        "0002_phase9_ecosystem": "0002_ecosystem_features",
    }

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This compatibility operation requires PostgreSQL.")

        legacy_app_label = "phase" + "9"
        with transaction.atomic(), connection.cursor() as cursor:
            existing_tables = set(connection.introspection.table_names(cursor))

            for old_name, new_name in self.TABLE_RENAMES.items():
                old_exists = old_name in existing_tables
                new_exists = new_name in existing_tables
                if old_exists and new_exists:
                    raise CommandError(
                        f"Both legacy and new tables exist ({old_name}, {new_name}); "
                        "manual data reconciliation is required. No changes were made."
                    )
                if old_exists:
                    cursor.execute(
                        f"ALTER TABLE {connection.ops.quote_name(old_name)} "
                        f"RENAME TO {connection.ops.quote_name(new_name)}"
                    )
                    self.stdout.write(f"Renamed table: {old_name} -> {new_name}")

                    constraints = connection.introspection.get_constraints(cursor, new_name)
                    for old_constraint, details in list(constraints.items()):
                        if not old_constraint.startswith("phase9_"):
                            continue
                        new_constraint = old_constraint.replace("phase9_", "ecosystem_", 1)
                        if details.get("type") in {"pk", "uq", "fk", "check"}:
                            cursor.execute(
                                f"ALTER TABLE {connection.ops.quote_name(new_name)} "
                                f"RENAME CONSTRAINT {connection.ops.quote_name(old_constraint)} "
                                f"TO {connection.ops.quote_name(new_constraint)}"
                            )
                        elif details.get("type") == "idx":
                            cursor.execute(
                                f"ALTER INDEX {connection.ops.quote_name(old_constraint)} "
                                f"RENAME TO {connection.ops.quote_name(new_constraint)}"
                            )

            if "django_migrations" in existing_tables:
                cursor.execute(
                    "SELECT name FROM django_migrations WHERE app = %s",
                    [legacy_app_label],
                )
                old_migrations = [row[0] for row in cursor.fetchall()]
                for old_migration in old_migrations:
                    new_migration = self.MIGRATION_RENAMES.get(old_migration)
                    if not new_migration:
                        new_migration = old_migration.replace("phase9", "ecosystem")
                    cursor.execute(
                        "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
                        ["ecosystem", new_migration],
                    )
                    if cursor.fetchone():
                        cursor.execute(
                            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
                            [legacy_app_label, old_migration],
                        )
                    else:
                        cursor.execute(
                            "UPDATE django_migrations SET app = %s, name = %s "
                            "WHERE app = %s AND name = %s",
                            ["ecosystem", new_migration, legacy_app_label, old_migration],
                        )

            if "django_content_type" in existing_tables:
                cursor.execute(
                    "SELECT 1 FROM django_content_type WHERE app_label = %s LIMIT 1",
                    ["ecosystem"],
                )
                ecosystem_content_types_exist = cursor.fetchone() is not None
                cursor.execute(
                    "SELECT 1 FROM django_content_type WHERE app_label = %s LIMIT 1",
                    [legacy_app_label],
                )
                legacy_content_types_exist = cursor.fetchone() is not None
                if ecosystem_content_types_exist and legacy_content_types_exist:
                    raise CommandError(
                        "Both legacy and ecosystem content types exist. "
                        "Resolve content-type collisions before continuing."
                    )
                if legacy_content_types_exist:
                    cursor.execute(
                        "UPDATE django_content_type SET app_label = %s WHERE app_label = %s",
                        ["ecosystem", legacy_app_label],
                    )

        self.stdout.write(self.style.SUCCESS(
            "Legacy schema adoption completed. You can now run: python manage.py migrate"
        ))
