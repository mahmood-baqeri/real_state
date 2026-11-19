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
    display_name: str
    tile_url: str
    dark_tile_url: str
    attribution: str
    max_zoom: int = 18
    requires_api_key: bool = False


class MapProviderBase(ABC):
    provider_key: str
    display_name: str

    @abstractmethod
    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        raise NotImplementedError

    @abstractmethod
    def get_client_tile_config(
        self,
        *,
        custom_tile_url: str = "",
        api_key: str = "",
    ) -> MapClientConfig:
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
    display_name = "OpenStreetMap Standard"

    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        return GeoCoordinate(latitude=Decimal("35.689200"), longitude=Decimal("51.389000"))

    def get_client_tile_config(
        self, *, custom_tile_url: str = "", api_key: str = ""
    ) -> MapClientConfig:
        return MapClientConfig(
            provider_key=self.provider_key,
            display_name=self.display_name,
            tile_url=custom_tile_url or "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            dark_tile_url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attribution="&copy; OpenStreetMap contributors",
            max_zoom=18,
            requires_api_key=False,
        )


class CartoPositronAdapter(MapProviderBase):
    provider_key = "carto"
    display_name = "CartoDB Architectural (Light & Dark)"

    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        return GeoCoordinate(latitude=Decimal("35.757500"), longitude=Decimal("51.410000"))

    def get_client_tile_config(
        self, *, custom_tile_url: str = "", api_key: str = ""
    ) -> MapClientConfig:
        return MapClientConfig(
            provider_key=self.provider_key,
            display_name=self.display_name,
            tile_url=custom_tile_url or "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            dark_tile_url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attribution="&copy; OpenStreetMap &copy; CARTO",
            max_zoom=19,
            requires_api_key=False,
        )


class NeshanMapAdapter(MapProviderBase):
    provider_key = "neshan"
    display_name = "نقشه نشان (Neshan)"

    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        return GeoCoordinate(latitude=Decimal("35.757500"), longitude=Decimal("51.410000"))

    def get_client_tile_config(
        self, *, custom_tile_url: str = "", api_key: str = ""
    ) -> MapClientConfig:
        fallback = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        tile = custom_tile_url or (
            f"https://static.neshan.org/sdk/leaflet/1.4.0/neshan-tile/{{z}}/{{x}}/{{y}}.png"
            if api_key
            else fallback
        )
        return MapClientConfig(
            provider_key=self.provider_key,
            display_name=self.display_name,
            tile_url=tile,
            dark_tile_url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attribution="&copy; Neshan / OpenStreetMap",
            max_zoom=18,
            requires_api_key=True,
        )


class CustomTileMapAdapter(MapProviderBase):
    provider_key = "custom_tile"
    display_name = "سرویس نقشه سفارشی (Custom XYZ Tile)"

    def geocode(self, address: str, country_code: str = "IR") -> Optional[GeoCoordinate]:
        return GeoCoordinate(latitude=Decimal("35.689200"), longitude=Decimal("51.389000"))

    def get_client_tile_config(
        self, *, custom_tile_url: str = "", api_key: str = ""
    ) -> MapClientConfig:
        url = custom_tile_url or "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        return MapClientConfig(
            provider_key=self.provider_key,
            display_name=self.display_name,
            tile_url=url,
            dark_tile_url=url,
            attribution="&copy; Custom Map Tile Provider",
            max_zoom=18,
            requires_api_key=False,
        )
