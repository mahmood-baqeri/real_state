"""Read-only database/schema diagnostics for the Django project.

Run with:
    python manage.py diagnose_schema
    python manage.py diagnose_schema --app documents

This command never creates, alters, or deletes database objects.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder

class Command(BaseCommand):
    help = "Compare installed Django model columns with the connected database (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")
        parser.add_argument("--app", dest="app_label")

    def handle(self, *args, **options):
        alias = options["database"]
        app_label = options.get("app_label")
        if alias not in connections:
            raise CommandError(f"Unknown database alias: {alias}")

        connection = connections[alias]
        try:
            connection.ensure_connection()
        except Exception as exc:
            raise CommandError(f"Cannot connect to database '{alias}': {exc}") from exc

        self.stdout.write(self.style.HTTP_INFO(
            f"Database alias: {alias} | vendor: {connection.vendor} | "
            f"database: {connection.settings_dict.get('NAME')} | "
            f"host: {connection.settings_dict.get('HOST')} | "
            f"port: {connection.settings_dict.get('PORT')}"
        ))

        existing_tables = set(connection.introspection.table_names())
        models = [
            model for model in apps.get_models()
            if not model._meta.proxy
            and (not app_label or model._meta.app_label == app_label)
        ]
        missing_tables = []
        missing_columns = []
        checked_tables = set()

        with connection.cursor() as cursor:
            for model in models:
                table = model._meta.db_table
                if table in checked_tables:
                    continue
                checked_tables.add(table)
                if table not in existing_tables:
                    missing_tables.append((model._meta.label, table))
                    continue
                actual_columns = {
                    column.name
                    for column in connection.introspection.get_table_description(cursor, table)
                }
                for field in model._meta.concrete_fields:
                    column = field.column
                    if column and column not in actual_columns:
                        missing_columns.append((model._meta.label, table, column))

        try:
            applied = MigrationRecorder(connection).applied_migrations()
        except Exception as exc:
            raise CommandError(f"Could not read django_migrations: {exc}") from exc

        docs_0002 = ("documents", "0002_document_deleted_at_document_deleted_by_and_more")
        if app_label in (None, "documents"):
            state = "APPLIED" if docs_0002 in applied else "NOT APPLIED"
            self.stdout.write(f"Migration documents.0002: {state}")
            expected = {"is_deleted", "deleted_at", "deleted_by_id"}
            if "documents_document" in existing_tables:
                with connection.cursor() as cursor:
                    actual = {
                        column.name
                        for column in connection.introspection.get_table_description(
                            cursor, "documents_document"
                        )
                    }
                absent = sorted(expected - actual)
                if absent:
                    self.stdout.write(self.style.ERROR(
                        "documents_document missing columns: " + ", ".join(absent)
                    ))

        if missing_tables:
            self.stdout.write(self.style.ERROR(f"Missing tables ({len(missing_tables)}):"))
            for label, table in missing_tables:
                self.stdout.write(f"  - {label}: {table}")
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"Missing columns ({len(missing_columns)}):"))
            for label, table, column in missing_columns:
                self.stdout.write(f"  - {label} [{table}].{column}")

        if not missing_tables and not missing_columns:
            self.stdout.write(self.style.SUCCESS(
                f"Schema check passed for {len(checked_tables)} model tables."
            ))
        else:
            raise CommandError(
                f"Schema mismatch: {len(missing_tables)} missing tables and "
                f"{len(missing_columns)} missing columns. No database changes were made."
            )
