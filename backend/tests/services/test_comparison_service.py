from decimal import Decimal

from app.services.comparison_service import calculate_change


def test_calculate_change_uses_later_minus_base_and_absolute_denominator():
    result = calculate_change(Decimal(-100), Decimal(-75))

    assert result.absolute_change == Decimal(25)
    assert result.percentage_change == Decimal(25)
    assert result.change_status == "CALCULATED"


def test_calculate_change_handles_zero_missing_and_null_without_nan():
    assert calculate_change(Decimal(0), Decimal(10)).change_status == "NEW"
    assert calculate_change(Decimal(0), Decimal(0)).change_status == "UNCHANGED"
    assert calculate_change(None, Decimal(10), base_present=False).change_status == "NEW"
    assert (
        calculate_change(Decimal(10), None, comparison_present=False).change_status
        == "REMOVED"
    )
    assert calculate_change(None, Decimal(10), base_present=True).change_status == "NO_BASE"
