from decimal import Decimal
from pathlib import Path

from app.importers.excel_reader import read_workbook
from app.importers.header_detector import detect_header
from app.importers.sheet_classifier import classify_sheet
from app.services.account_extraction_service import extract_account_candidates

EXAMPLES_DIR = Path("data/examples")


def test_real_xlsx_examples_can_be_read_without_modifying_them():
    examples = sorted(EXAMPLES_DIR.glob("*.xlsx"))

    assert examples, "No se encontraron archivos .xlsx en data/examples"

    for example in examples:
        workbook = read_workbook(example)
        assert workbook.path == example
        assert workbook.sheets
        assert any(sheet.rows for sheet in workbook.sheets)


def test_real_xlsx_examples_produce_at_least_one_known_sheet_type():
    known_classifications = []

    for example in sorted(EXAMPLES_DIR.glob("*.xlsx")):
        workbook = read_workbook(example)
        known_classifications.extend(
            classify_sheet(sheet.name, sheet.rows)
            for sheet in workbook.sheets
        )

    assert any(result.confidence > 0 for result in known_classifications)


def test_statement_examples_produce_candidates_without_explicit_headers():
    workbook = read_workbook(EXAMPLES_DIR / "2025-ER BENGALA.xlsx")
    candidates = []
    for sheet in workbook.sheets:
        candidates.extend(extract_account_candidates(sheet, detect_header(sheet.rows)))

    assert len(candidates) > 0
    assert any(candidate.name == "INGRESOS POR SERVICIOS" for candidate in candidates)


def test_bengala_2024_preserves_declared_lines():
    workbook = read_workbook(EXAMPLES_DIR / "2025-ER BENGALA.xlsx")
    sheet = next(item for item in workbook.sheets if item.name == "2024")

    by_name = {
        candidate.name: candidate
        for candidate in extract_account_candidates(sheet, detect_header(sheet.rows))
    }

    assert by_name["INGRESOS POR SERVICIOS"].ending_balance == Decimal("12000.00")
    assert by_name["GASTOS DE ADMINISTRACION"].ending_balance == Decimal("1041.57")
    assert by_name["UTILIDAD DEL EJERCICIO"].ending_balance == Decimal("5608.04")
