from datetime import datetime, timezone as dt_timezone
from typing import Tuple
import jdatetime


class CalendarAdapter:
    """
    Stores and computes all timestamps in UTC, while providing clean Jalali / Gregorian
    period boundaries and display formatting based on agency or user preference.
    """

    @staticmethod
    def format_date(dt: datetime, calendar_type: str = "jalali") -> str:
        utc_dt = dt.astimezone(dt_timezone.utc) if dt.tzinfo else dt.replace(tzinfo=dt_timezone.utc)
        if calendar_type == "jalali":
            jdt = jdatetime.datetime.fromgregorian(datetime=utc_dt)
            return jdt.strftime("%Y/%m/%d")
        return utc_dt.strftime("%Y-%m-%d")

    @staticmethod
    def jalali_month_bounds_utc(jy: int, jm: int) -> Tuple[datetime, datetime]:
        start_j = jdatetime.datetime(jy, jm, 1, 0, 0, 0)
        if jm == 12:
            next_j = jdatetime.datetime(jy + 1, 1, 1, 0, 0, 0)
        else:
            next_j = jdatetime.datetime(jy, jm + 1, 1, 0, 0, 0)
        start_g = start_j.togregorian().replace(tzinfo=dt_timezone.utc)
        end_g = next_j.togregorian().replace(tzinfo=dt_timezone.utc)
        return start_g, end_g

    @staticmethod
    def gregorian_month_bounds_utc(gy: int, gm: int) -> Tuple[datetime, datetime]:
        start_g = datetime(gy, gm, 1, 0, 0, 0, tzinfo=dt_timezone.utc)
        if gm == 12:
            end_g = datetime(gy + 1, 1, 1, 0, 0, 0, tzinfo=dt_timezone.utc)
        else:
            end_g = datetime(gy, gm + 1, 1, 0, 0, 0, tzinfo=dt_timezone.utc)
        return start_g, end_g
