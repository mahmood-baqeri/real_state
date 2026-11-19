from decimal import Decimal, ROUND_HALF_UP

AREA_UNIT_TO_SQM = {
    "SQM": Decimal("1"),
    "SQFT": Decimal("0.09290304"),
    "HECTARE": Decimal("10000"),
}


class AreaUnitConverter:
    @staticmethod
    def to_sqm(value: Decimal, from_unit: str) -> Decimal:
        factor = AREA_UNIT_TO_SQM.get(from_unit.upper())
        if factor is None:
            raise ValueError(f"Unsupported area unit: {from_unit}")
        return (Decimal(value) * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def from_sqm(sqm_value: Decimal, to_unit: str) -> Decimal:
        factor = AREA_UNIT_TO_SQM.get(to_unit.upper())
        if factor is None:
            raise ValueError(f"Unsupported area unit: {to_unit}")
        return (Decimal(sqm_value) / factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
