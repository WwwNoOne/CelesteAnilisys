from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ChangeResult:
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    change_status: str


def calculate_change(
    base_value: Decimal | None,
    comparison_value: Decimal | None,
    *,
    base_present: bool = True,
    comparison_present: bool = True,
) -> ChangeResult:
    if not base_present:
        return ChangeResult(comparison_value, None, "NEW")
    if not comparison_present:
        absolute = -base_value if base_value is not None else None
        return ChangeResult(absolute, None, "REMOVED")
    if base_value is None or comparison_value is None:
        return ChangeResult(None, None, "NO_BASE")

    absolute = comparison_value - base_value
    if base_value == 0:
        status = "UNCHANGED" if comparison_value == 0 else "NEW"
        return ChangeResult(absolute, None, status)

    percentage = (absolute / abs(base_value)) * Decimal(100)
    return ChangeResult(absolute, percentage, "CALCULATED")
