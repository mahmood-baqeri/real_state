# Path: backend/django_core/integrations/maps.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
import math
from typing import Optional


@dataclass(frozen=True)
class GeoCoordinate:
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True)
class MapClientConfig:
    provider_key: str
    tile_url: str
    attribution: str


class MapProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        raise NotImplementedError

    @abstractmethod
    def get_client_tile_config(self) -> MapClientConfig:
        raise NotImplementedError

    @staticmethod
    def haversine_meters(a: GeoCoordinate, b: GeoCoordinate) -> int:
        r = 6371000
        phi1 = math.radians(float(a.latitude))
        phi2 = math.radians(float(b.latitude))
        dphi = math.radians(float(b.latitude - a.latitude))
        dlambda = math.radians(float(b.longitude - a.longitude))
        val = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return int(2 * r * math.atan2(math.sqrt(val), math.sqrt(1 - val)))


class OpenStreetMapAdapter(MapProviderBase):
    provider_key = "osm"

    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        # Deterministic development coordinate fallback for Tehran center
        return GeoCoordinate(latitude=Decimal("35.689200"), longitude=Decimal("51.389000"))

    def get_client_tile_config(self) -> MapClientConfig:
        return MapClientConfig(
            provider_key=self.provider_key,
            tile_url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            attribution="OpenStreetMap contributors",
        )
