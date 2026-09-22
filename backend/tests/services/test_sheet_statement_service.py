from datetime import date
from decimal import Decimal

from app.schemas.import_analysis import SheetSnapshot
from app.services.sheet_statement_service import analyze_sheet


def test_valid_sheet_exposes_two_independent_lateral_blocks():
    sheet = SheetSnapshot(
        name="Balance General 2024",
        rows=[
            ["BALANCE GENERAL AL 31 DE DICIEMBRE DE 2024"],
            ["ACTIVO", Decimal(50000), None, None, "PASIVO", Decimal(30000)],
        ],
    )

    decision = analyze_sheet(sheet, "empresa.xlsx")

    assert decision.valid is True
    assert decision.statement_type == "ESTADO_SITUACION_FINANCIERA"
    assert decision.as_of_date == date(2024, 12, 31)
    assert [(c.text_column, c.amount_column) for c in decision.candidates] == [(0, 1), (4, 5)]


def test_auxiliary_sheet_without_financial_blocks_is_discarded():
    sheet = SheetSnapshot(name="Firmas", rows=[["REPRESENTANTE LEGAL"], ["CONTADOR"]])

    decision = analyze_sheet(sheet, "empresa.xlsx")

    assert decision.valid is False
    assert decision.discard_reason == "No contiene cuentas con saldos"


def test_sheet_with_two_explicit_statement_titles_is_discarded():
    sheet = SheetSnapshot(
        name="Reportes",
        rows=[
            ["BALANCE GENERAL"],
            ["ACTIVO", 100],
            ["ESTADO DE RESULTADOS"],
            ["INGRESOS", 100],
        ],
    )

    decision = analyze_sheet(sheet, "empresa.xlsx")

    assert decision.valid is False
    assert decision.discard_reason == "Contiene más de un estado financiero"


def test_each_sheet_detects_its_own_period():
    first = SheetSnapshot(
        name="Resultados 2024",
        rows=[["ESTADO DE RESULTADOS DEL 1 DE ENERO AL 31 DE DICIEMBRE DE 2024"], ["INGRESOS", 10]],
    )
    second = SheetSnapshot(
        name="Resultados 2025",
        rows=[["ESTADO DE RESULTADOS DEL 1 DE ENERO AL 31 DE DICIEMBRE DE 2025"], ["INGRESOS", 20]],
    )

    decisions = [analyze_sheet(first, "empresa.xlsx"), analyze_sheet(second, "empresa.xlsx")]

    assert [item.period_year for item in decisions] == [2024, 2025]
    assert [item.period_end for item in decisions] == [date(2024, 12, 31), date(2025, 12, 31)]
