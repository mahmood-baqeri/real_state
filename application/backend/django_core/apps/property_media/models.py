from django.db import models
from common.models import BaseModel


class PropertyMedia(BaseModel):
    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        FLOORPLAN = "FLOORPLAN", "Floor Plan"
        VIRTUAL_TOUR = "VIRTUAL_TOUR", "Virtual Tour"
        DOCUMENT = "DOCUMENT", "Document"

    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="media_items"
    )
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.IMAGE)
    file_key = models.CharField(max_length=255, blank=True, default="")
    legacy_public_file_key = models.CharField(max_length=255, blank=True, default="")
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=120, blank=True, default="")
    is_cover = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "property_media_item"
        ordering = ["sort_order", "created_at"]
