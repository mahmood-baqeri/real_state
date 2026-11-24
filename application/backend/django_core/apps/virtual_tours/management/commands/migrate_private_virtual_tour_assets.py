from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.virtual_tours.models import (
    Scene, CaptureImage, PanoramaVersion, FloorPlanAsset, GeneratedModelAsset, ScanAsset,
)
from integrations.registry import get_storage_provider


ASSET_FIELDS = [
    (Scene, ("thumbnail_storage_key",), "scene"),
    (CaptureImage, ("storage_key",), "capture_image"),
    (PanoramaVersion, ("storage_key", "thumbnail_key"), "panorama_version"),
    (FloorPlanAsset, ("storage_key", "preview_storage_key"), "floorplan"),
    (GeneratedModelAsset, ("storage_key",), "generated_model"),
    (ScanAsset, ("storage_key", "preview_glb_key", "density_map_key"), "scan"),
]


def _get_tour(obj, model):
    if model is Scene:
        return obj.tour
    if model is CaptureImage:
        return obj.session.tour
    if model is PanoramaVersion:
        return obj.scene.tour
    return obj.tour


class Command(BaseCommand):
    help = "Move legacy virtual-tour assets from public media storage to the private storage root."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = max(1, min(options["batch_size"], 1000))
        storage = get_storage_provider()
        migrated = 0
        for model, fields, label in ASSET_FIELDS:
            queryset = model._base_manager.all().select_related()
            for obj in queryset.iterator(chunk_size=batch_size):
                tour = _get_tour(obj, model)
                for field in fields:
                    old_key = getattr(obj, field, "") or ""
                    if not old_key:
                        continue
                    try:
                        content = storage.get_bytes(file_key=old_key)
                        if old_key.startswith("private/"):
                            continue
                    except Exception:
                        try:
                            content = storage.get_legacy_public_bytes(file_key=old_key)
                        except Exception as exc:
                            raise CommandError(
                                f"Legacy asset is missing: {model.__name__} pk={obj.pk} field={field} key={old_key}: {exc}"
                            ) from exc
                    try:
                        filename = Path(old_key).name
                        new_key = storage.put_bytes(
                            key_prefix=f"private/virtual_tours/{tour.agency_id}/{tour.id}/legacy/{label}/{obj.pk}",
                            safe_filename=filename,
                            content=content,
                            mime_type="application/octet-stream",
                        ).file_key
                        if dry_run:
                            storage.delete_object(file_key=new_key)
                            migrated += 1
                            continue
                        setattr(obj, field, new_key)
                        with transaction.atomic():
                            obj.save(update_fields=[field, "updated_at"])
                        storage.delete_legacy_public_object(file_key=old_key)
                        migrated += 1
                    except Exception as exc:
                        raise CommandError(
                            f"Could not migrate {model.__name__} pk={obj.pk} field={field} key={old_key}: {exc}"
                        ) from exc
        self.stdout.write(self.style.SUCCESS(
            f"{'Would migrate' if dry_run else 'Migrated'} {migrated} virtual-tour assets."
        ))
