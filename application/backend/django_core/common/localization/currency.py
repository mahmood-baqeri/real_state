from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
from django.core.cache import cache

CURRENCY_DECIMALS_CACHE_KEY = "bonyan:currency:decimals"
FX_RATES_CACHE_KEY = "bonyan:fx:rates_map"
DEFAULT_FALLBACK_DECIMALS = {"IRR": 0, "IRT": 0}


def invalidate_currency_cache() -> None:
    try:
        cache.delete(CURRENCY_DECIMALS_CACHE_KEY)
        cache.delete(FX_RATES_CACHE_KEY)
    except Exception:
        pass


def _get_decimal_places_map() -> Dict[str, int]:
    try:
        cached = cache.get(CURRENCY_DECIMALS_CACHE_KEY)
        if isinstance(cached, dict) and cached:
            return cached
    except Exception:
        pass

    try:
        from apps.settings.models import Currency

        rows = {
            c.code.upper(): int(c.decimal_places)
            for c in Currency.objects.filter(is_active=True)
        }
        if rows:
            try:
                cache.set(CURRENCY_DECIMALS_CACHE_KEY, rows, timeout=300)
            except Exception:
                pass
            return rows
    except Exception:
        pass
    return dict(DEFAULT_FALLBACK_DECIMALS)


def _get_fx_map() -> Dict[tuple[str, str], Decimal]:
    try:
        cached = cache.get(FX_RATES_CACHE_KEY)
        if isinstance(cached, dict) and cached:
            return {k: Decimal(str(v)) for k, v in cached.items()}
    except Exception:
        pass

    fx_map: Dict[tuple[str, str], Decimal] = {}
    try:
        from apps.settings.models import ExchangeRate

        for row in ExchangeRate.objects.filter(
            is_active=True,
            base_currency__is_active=True,
            quote_currency__is_active=True,
        ).only("base_currency_id", "quote_currency_id", "rate"):
            src = row.base_currency_id.upper()
            dst = row.quote_currency_id.upper()
            fx_map[(src, dst)] = Decimal(row.rate)
        if fx_map:
            try:
                cache.set(
                    FX_RATES_CACHE_KEY,
                    {k: str(v) for k, v in fx_map.items()},
                    timeout=300,
                )
            except Exception:
                pass
    except Exception:
        pass
    return fx_map


def quantize_amount(amount: Decimal, currency_code: str = "IRT") -> Decimal:
    decimals_map = _get_decimal_places_map()
    places = decimals_map.get(currency_code.upper(), 2)
    quantum = Decimal("1") if places == 0 else Decimal(f"1e-{places}")
    return Decimal(amount).quantize(quantum, rounding=ROUND_HALF_UP)


class CurrencyConversionService:
    """Explicit DB-backed Decimal-only currency conversion without implicit assumptions."""

    @staticmethod
    def _direct_or_inverse_rate(
        fx_map: Dict[tuple[str, str], Decimal], src: str, dst: str
    ) -> Optional[Decimal]:
        if (src, dst) in fx_map:
            return fx_map[(src, dst)]
        inv = fx_map.get((dst, src))
        if inv and inv > Decimal("0"):
            return (Decimal("1") / inv).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
        return None

    @classmethod
    def get_rate(cls, from_currency: str, to_currency: str) -> Decimal:
        src = from_currency.upper()
        dst = to_currency.upper()
        if src == dst:
            return Decimal("1.000000")

        fx_map = _get_fx_map()
        direct = cls._direct_or_inverse_rate(fx_map, src, dst)
        if direct is not None:
            return direct.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        # Single-hop triangulation across active currencies in FX table
        pivots = {pair[0] for pair in fx_map.keys()} | {pair[1] for pair in fx_map.keys()}
        for pivot in pivots:
            if pivot in (src, dst):
                continue
            leg1 = cls._direct_or_inverse_rate(fx_map, src, pivot)
            leg2 = cls._direct_or_inverse_rate(fx_map, pivot, dst)
            if leg1 is not None and leg2 is not None:
                return (leg1 * leg2).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        raise ValueError(f"Explicit exchange rate required for {src} -> {dst}.")

    @classmethod
    def get_snapshot_rate_to_base(cls, from_currency: str, base_currency: str = "IRT") -> Decimal:
        try:
            return cls.get_rate(from_currency, base_currency)
        except ValueError:
            return Decimal("1.000000")

    @classmethod
    def convert(cls, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        rate = cls.get_rate(from_currency, to_currency)
        return quantize_amount(Decimal(amount) * rate, to_currency)

    @classmethod
    def convert_rial_toman(cls, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        src = from_currency.upper()
        dst = to_currency.upper()
        if src == dst:
            return quantize_amount(Decimal(amount), dst)
        try:
            return cls.convert(amount, src, dst)
        except ValueError:
            # Fallback to Currency.base_unit_factor in DB if FX rows aren't created yet
            try:
                from apps.settings.models import Currency

                c_src = Currency.objects.filter(code=src, is_active=True).first()
                c_dst = Currency.objects.filter(code=dst, is_active=True).first()
                if c_src and c_dst and c_dst.base_unit_factor > Decimal("0"):
                    converted = (Decimal(amount) * c_src.base_unit_factor) / c_dst.base_unit_factor
                    return quantize_amount(converted, dst)
            except Exception:
                pass
            raise ValueError(f"Explicit exchange rate required for {src} -> {dst}.")

    @staticmethod
    def convert_with_rate(amount: Decimal, rate: Decimal, to_currency: str) -> Decimal:
        result = Decimal(amount) * Decimal(rate)
        return quantize_amount(result, to_currency)
