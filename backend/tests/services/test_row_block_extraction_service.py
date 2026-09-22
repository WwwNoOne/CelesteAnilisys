from decimal import Decimal

from app.services.row_block_extraction_service import extract_row_blocks


def test_amount_belongs_to_previous_text_across_empty_cells():
    blocks = extract_row_blocks(["Ingresos", None, None, 12000, "Conciliación", None])

    assert [(block.text, block.amount) for block in blocks] == [
        ("Ingresos", Decimal("12000.00")),
        ("Conciliación", None),
    ]


def test_two_lateral_text_amount_blocks_are_independent():
    blocks = extract_row_blocks(["Activo", 50000, None, "Pasivo", None, 30000])

    assert [(block.text, block.amount) for block in blocks] == [
        ("Activo", Decimal("50000.00")),
        ("Pasivo", Decimal("30000.00")),
    ]


def test_explicit_zero_survives_and_empty_row_disappears():
    assert extract_row_blocks(["Costo", None, 0])[0].amount == Decimal("0.00")
    assert extract_row_blocks([None, "", None]) == []


def test_number_before_text_is_not_assigned_forward():
    blocks = extract_row_blocks([2025, "Ventas", 10])

    assert [(block.text, block.amount) for block in blocks] == [
        ("Ventas", Decimal("10.00"))
    ]


def test_first_number_is_declared_balance_when_block_has_more_numbers():
    block = extract_row_blocks(["Cuenta", None, 15, 99])[0]

    assert (block.amount, block.amount_column) == (Decimal("15.00"), 2)
