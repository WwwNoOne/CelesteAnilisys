from datetime import date

from app.schemas.import_analysis import SheetSnapshot
from app.services.period_detection_service import (
    detect_period,
    parse_statement_dates,
)


def test_detects_year_from_sheet_name_before_file_name():
    result = detect_period(
        "reporte-2024.xlsx",
        [SheetSnapshot(name="Estado de Resultados 2025", rows=[["Ingresos"]])],
    )

    assert result.year == 2025
    assert result.label == "2025"
    assert result.source == "sheet_name"
    assert result.conflict is False


def test_detects_year_from_title_when_sheet_name_has_no_year():
    result = detect_period(
        "reporte.xlsx",
        [SheetSnapshot(name="Resultados", rows=[["Estado de Resultados del 1 de Enero al 31 de Diciembre de 2025"]])],
    )

    assert result.year == 2025
    assert result.source == "sheet_title"


def test_detects_year_from_file_name_as_fallback():
    result = detect_period("Bengala-2024.xlsx", [SheetSnapshot(name="Resultados", rows=[["Ingresos"]])])

    assert result.year == 2024
    assert result.source == "file_name"


def test_reports_conflict_when_sheets_have_different_years():
    result = detect_period(
        "reporte.xlsx",
        [
            SheetSnapshot(name="2024", rows=[["Ingresos"]]),
            SheetSnapshot(name="2025", rows=[["Ingresos"]]),
        ],
    )

    assert result.conflict is True
    assert result.year is None


def test_returns_unvalidated_result_when_year_is_not_detectable():
    result = detect_period("reporte.xlsx", [SheetSnapshot(name="Resultados", rows=[["Ingresos"]])])

    assert result.year is None
    assert result.label is None
    assert result.confidence == 0


def test_parses_income_statement_date_range():
    parsed = parse_statement_dates("Estado de Resultados del 1 de Enero al 31 de Diciembre de 2025")
    assert parsed["period_start"] == date(2025, 1, 1)
    assert parsed["period_end"] == date(2025, 12, 31)
    assert parsed["as_of_date"] == date(2025, 12, 31)
    assert parsed["timeframe"] == "ANNUAL"
    assert parsed["year"] == 2025


def test_parses_balance_sheet_as_of_date():
    parsed = parse_statement_dates("Balance General Al 31 de Diciembre de 2025")
    assert parsed["as_of_date"] == date(2025, 12, 31)
    assert parsed["period_start"] is None
    assert parsed["period_end"] is None
    assert parsed["timeframe"] == "YEAR_END"
    assert parsed["year"] == 2025


def test_parses_monthly_income_statement_range():
    parsed = parse_statement_dates("Estado de Resultados del 01/01/2025 al 31/03/2025")
    assert parsed["period_start"] == date(2025, 1, 1)
    assert parsed["period_end"] == date(2025, 3, 31)
    assert parsed["timeframe"] == "QUARTERLY"
