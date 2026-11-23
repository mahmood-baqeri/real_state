from django.contrib import admin
from django.urls import path

# Django operates strictly as the Core ORM, Domain Logic & Admin/Worker engine.
# All HTTP Web APIs are served exclusively by FastAPI (/api/v1/*).
urlpatterns = [
    path("admin/", admin.site.urls),
]
