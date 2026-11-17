from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

CURRENCY_UNIT_FACTORS_TO_IRR: Dict[str, Decimal] = {
    "IRR": Decimal("1"),
    "IRT": Decimal("10"),
}

CURRENCY_DECIMAL_PLACES: Dict[str, int] = {
    "IRR": 0,
    "IRT": 0,
    "USD": 2,
    "EUR": 2,
    "AED": 2,
}


def quantize_amount(amount: Decimal, currency_code: str = "IRT") -> Decimal:
    places = CURRENCY_DECIMAL_PLACES.get(currency_code.upper(), 2)
    quantum = Decimal("1") if places == 0 else Decimal(f"1e-{places}")
    return Decimal(amount).quantize(quantum, rounding=ROUND_HALF_UP)


class CurrencyConversionService:
    """Explicit Decimal-only currency conversion without implicit assumptions."""

    @staticmethod
    def convert_rial_toman(amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        src = from_currency.upper()
        dst = to_currency.upper()
        if src == dst:
            return quantize_amount(Decimal(amount), dst)
        if src not in CURRENCY_UNIT_FACTORS_TO_IRR or dst not in CURRENCY_UNIT_FACTORS_TO_IRR:
            raise ValueError(f"Explicit exchange rate required for {src} -> {dst}.")
        irr_value = Decimal(amount) * CURRENCY_UNIT_FACTORS_TO_IRR[src]
        converted = irr_value / CURRENCY_UNIT_FACTORS_TO_IRR[dst]
        return quantize_amount(converted, dst)

    @staticmethod
    def convert_with_rate(amount: Decimal, rate: Decimal, to_currency: str) -> Decimal:
        result = Decimal(amount) * Decimal(rate)
        return quantize_amount(result, to_currency)
