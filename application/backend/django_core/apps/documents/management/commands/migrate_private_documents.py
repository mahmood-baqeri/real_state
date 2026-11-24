"""Move legacy public document objects to private storage, with resumable cleanup."""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.documents.models import DocumentVersion
from integrations.registry import get_storage_provider
from common.tenant.context import tenant_bypass


class Command(BaseCommand):
    help = "Move legacy document objects into private storage and remove public originals."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = max(1, min(options["batch_size"], 500))
        storage = get_storage_provider()
        copied = cleaned = skipped = 0
        with tenant_bypass(reason="private_media_migration"):
            qs = DocumentVersion.objects.select_related("document").order_by("id")
            for version in qs.iterator(chunk_size=batch_size):
                old_key = version.legacy_public_file_key or ""
                if old_key:
                    self.stdout.write(f"{'Would clean' if dry_run else 'Cleaning'} public object {old_key}")
                    if not dry_run:
                        storage.delete_legacy_public_object(file_key=old_key)
                        version.legacy_public_file_key = ""
                        version.save(update_fields=["legacy_public_file_key", "updated_at"])
                    cleaned += 1
                    continue

                key = version.file_key or ""
                if key.startswith("private/pending/"):
                    skipped += 1
                    continue
                if not key or key.startswith("/") or "\\\\" in key or any(part in ("", ".", "..") for part in Path(key).parts):
                    raise CommandError(f"Unsafe legacy file key on DocumentVersion {version.pk}: {key!r}")
                try:
                    payload = storage.get_bytes(file_key=key)
                    if key.startswith("private/"):
                        skipped += 1
                        continue
                except Exception:
                    try:
                        payload = storage.get_legacy_public_bytes(file_key=key)
                    except Exception as exc:
                        raise CommandError(
                            f"Legacy document object is missing: version={version.pk}, key={key!r}"
                        ) from exc
                safe_name = Path(key).name
                stored = storage.put_bytes(
                    key_prefix=f"private/agencies/{version.document.agency_id}/documents/migrated",
                    safe_filename=safe_name, content=payload, mime_type=version.mime_type or "application/octet-stream",
                )
                if storage.get_bytes(file_key=stored.file_key) != payload:
                    storage.delete_object(file_key=stored.file_key)
                    raise CommandError(f"Checksum/byte verification failed for DocumentVersion {version.pk}")
                self.stdout.write(f"{'Would migrate' if dry_run else 'Migrating'} {key} -> {stored.file_key}")
                if dry_run:
                    storage.delete_object(file_key=stored.file_key)
                else:
                    with transaction.atomic():
                        version.file_key = stored.file_key
                        version.legacy_public_file_key = key
                        version.save(update_fields=["file_key", "legacy_public_file_key", "updated_at"])
                    # If this fails, legacy_public_file_key is retained and the next run retries cleanup.
                    storage.delete_legacy_public_object(file_key=key)
                    version.legacy_public_file_key = ""
                    version.save(update_fields=["legacy_public_file_key", "updated_at"])
                copied += 1
        self.stdout.write(self.style.SUCCESS(
            f"Complete. copied={copied}, cleaned={cleaned}, skipped={skipped}, dry_run={dry_run}"
        ))
