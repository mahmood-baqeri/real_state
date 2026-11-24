from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.property_media.models import PropertyMedia
from integrations.registry import get_storage_provider
from common.tenant.context import tenant_bypass


class Command(BaseCommand):
    help = "Move property media into private storage and remove public originals safely."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = max(1, min(options["batch_size"], 1000))
        storage = get_storage_provider()
        moved = cleaned = skipped = 0
        with tenant_bypass(reason="private_media_migration"):
            qs = PropertyMedia.objects.select_related("property").exclude(file_key="").order_by("id")
            for media in qs.iterator(chunk_size=batch_size):
                if media.legacy_public_file_key:
                    if not dry_run:
                        storage.delete_legacy_public_object(file_key=media.legacy_public_file_key)
                        media.legacy_public_file_key = ""
                        media.save(update_fields=["legacy_public_file_key", "updated_at"])
                    cleaned += 1
                    continue
                try:
                    if media.file_key.startswith("/") or "\\" in media.file_key or "\x00" in media.file_key or any(part in ("", ".", "..") for part in Path(media.file_key).parts):
                        raise CommandError(f"Unsafe legacy file key on PropertyMedia {media.id}: {media.file_key!r}")
                    try:
                        content = storage.get_bytes(file_key=media.file_key)
                        if media.file_key.startswith("private/"):
                            if not dry_run:
                                media.url = f"/api/v1/properties/{media.property_id}/media/{media.id}/file"
                                media.save(update_fields=["url", "updated_at"])
                            skipped += 1
                            continue
                    except Exception:
                        content = storage.get_legacy_public_bytes(file_key=media.file_key)
                    safe_name = Path(media.file_key).name
                    stored = storage.put_bytes(
                        key_prefix=f"private/agencies/{media.property.agency_id}/properties/{media.property_id}",
                        safe_filename=safe_name, content=content, mime_type="application/octet-stream",
                    )
                    if storage.get_bytes(file_key=stored.file_key) != content:
                        storage.delete_object(file_key=stored.file_key)
                        raise CommandError(f"Verification failed for PropertyMedia {media.id}")
                    if dry_run:
                        storage.delete_object(file_key=stored.file_key)
                    else:
                        with transaction.atomic():
                            media.legacy_public_file_key = media.file_key
                            media.file_key = stored.file_key
                            media.url = f"/api/v1/properties/{media.property_id}/media/{media.id}/file"
                            media.save(update_fields=["legacy_public_file_key", "file_key", "url", "updated_at"])
                        storage.delete_legacy_public_object(file_key=media.legacy_public_file_key)
                        media.legacy_public_file_key = ""
                        media.save(update_fields=["legacy_public_file_key", "updated_at"])
                    moved += 1
                except Exception as exc:
                    raise CommandError(f"Could not migrate PropertyMedia id={media.id}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"Complete. moved={moved}, cleaned={cleaned}, skipped={skipped}, dry_run={dry_run}"
        ))
