import datetime
import json
import uuid
from decimal import Decimal
from pathlib import Path
from django.apps import apps as dj_apps
from django.core.management.base import BaseCommand
from django.db import models as dj_models
from apps.settings.seeding import seed_all_platform_data


def _toposort_models(domain_models: list[type[dj_models.Model]]) -> list[type[dj_models.Model]]:
    model_set = set(domain_models)
    deps: dict[type[dj_models.Model], set[type[dj_models.Model]]] = {}
    for m in domain_models:
        d = set()
        for f in m._meta.concrete_fields:
            if f.is_relation and f.related_model in model_set and f.related_model != m:
                d.add(f.related_model)
        deps[m] = d

    ordered: list[type[dj_models.Model]] = []
    remaining = list(domain_models)
    while remaining:
        progressed = False
        for m in list(remaining):
            if not (deps[m] - set(ordered)):
                ordered.append(m)
                remaining.remove(m)
                progressed = True
        if not progressed:
            ordered.append(remaining.pop(0))
    return ordered


def _sql_literal(field: dj_models.Field, value) -> str:
    if value is None:
        return "NULL"
    if isinstance(field, dj_models.BooleanField):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(field, dj_models.JSONField):
        encoded = json.dumps(value, ensure_ascii=False).replace("'", "''")
        return f"'{encoded}'::jsonb"
    if isinstance(field, dj_models.UUIDField) or isinstance(value, uuid.UUID):
        return f"'{str(value)}'::uuid"
    if isinstance(field, dj_models.DateTimeField) or isinstance(value, datetime.datetime):
        iso = value.isoformat() if isinstance(value, datetime.datetime) else str(value)
        return f"'{iso}'::timestamptz"
    if isinstance(field, dj_models.DateField) or isinstance(value, datetime.date):
        return f"'{value.isoformat()}'::date"
    if isinstance(field, (dj_models.DecimalField, dj_models.IntegerField, dj_models.FloatField)):
        if isinstance(value, Decimal):
            return str(value)
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _export_postgresql_seed_sql(output_path: Path) -> int:
    excluded_apps = {"admin", "auth", "contenttypes", "sessions", "messages"}
    explicit_models = [
        m for m in dj_apps.get_models() if m._meta.app_label not in excluded_apps
    ]
    ordered_models = _toposort_models(explicit_models)

    # Collect auto-created M2M join models (e.g., properties_property_amenities, cms_article_tags)
    m2m_through_models: list[type[dj_models.Model]] = []
    seen_tables: set[str] = set()
    for m in ordered_models:
        for m2m in m._meta.many_to_many:
            through = m2m.remote_field.through
            if through._meta.auto_created and through._meta.db_table not in seen_tables:
                seen_tables.add(through._meta.db_table)
                m2m_through_models.append(through)

    lines = [
        "-- =============================================================================",
        "-- Bonyan Melk (بنیان ملک) — Idempotent PostgreSQL Seed Script (All 29 Apps)",
        "-- Generated directly from Django ORM models via `python manage.py seed_all`",
        "-- Usage: psql \"$DATABASE_URL\" -f scripts/seed_all.sql",
        "-- =============================================================================",
        "BEGIN;",
        "",
    ]

    total_rows = 0
    for model in ordered_models + m2m_through_models:
        manager = model.objects
        qs = manager.all_tenants() if hasattr(manager, "all_tenants") else manager.all()
        rows = list(qs)
        if not rows:
            continue

        fields = list(model._meta.concrete_fields)
        self_fk_cols = [
            f.attname for f in fields if f.is_relation and f.related_model == model
        ]
        if self_fk_cols:
            rows.sort(
                key=lambda r: tuple(1 if getattr(r, c) is not None else 0 for c in self_fk_cols)
            )

        col_names = ", ".join(f'"{f.column}"' for f in fields)
        lines.append(f"-- {model._meta.label} ({len(rows)} rows)")
        for obj in rows:
            vals = ", ".join(_sql_literal(f, getattr(obj, f.attname)) for f in fields)
            lines.append(
                f'INSERT INTO "{model._meta.db_table}" ({col_names}) VALUES ({vals}) ON CONFLICT DO NOTHING;'
            )
            total_rows += 1

        pk = model._meta.pk
        if isinstance(pk, (dj_models.AutoField, dj_models.BigAutoField)):
            lines.append(
                f"SELECT setval(pg_get_serial_sequence('{model._meta.db_table}', '{pk.column}'), "
                f'COALESCE((SELECT MAX("{pk.column}") FROM "{model._meta.db_table}"), 1));'
            )
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return total_rows


class Command(BaseCommand):
    help = "Idempotently seeds all 29 domain apps (every table & all 7 user roles) and can export standalone PostgreSQL seed SQL."

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Suppress verbose model counts output.")
        parser.add_argument(
            "--export-sql",
            type=str,
            default="",
            help="Optional path to write a standalone idempotent PostgreSQL seed SQL script.",
        )

    def handle(self, *args, **options):
        quiet = options.get("quiet", False)
        export_sql = (options.get("export_sql") or "").strip()

        res = seed_all_platform_data(
            log_fn=None if quiet else self.stdout.write,
            verify_all=True,
        )
        if export_sql:
            written = _export_postgresql_seed_sql(Path(export_sql))
            if not quiet:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Exported {written} PostgreSQL INSERT statements to {export_sql}."
                    )
                )
        if not quiet:
            self.stdout.write(
                self.style.SUCCESS(
                    f"seed_all completed: {len(res['counts'])} domain tables verified non-empty."
                )
            )
