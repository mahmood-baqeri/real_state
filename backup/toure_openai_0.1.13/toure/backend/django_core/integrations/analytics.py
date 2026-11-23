from abc import ABC, abstractmethod
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AnalyticsProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def track_event(
        self,
        *,
        event_name: str,
        agency_id: Optional[str] = None,
        user_id: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        raise NotImplementedError


class InternalAnalyticsAdapter(AnalyticsProviderBase):
    provider_key = "internal"

    def track_event(
        self,
        *,
        event_name: str,
        agency_id: Optional[str] = None,
        user_id: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        logger.info(
            "[Analytics:%s] agency=%s user=%s props=%s",
            event_name,
            agency_id,
            user_id,
            properties or {},
        )
