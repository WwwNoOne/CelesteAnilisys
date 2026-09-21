from pathlib import Path

from app.importers.excel_reader import read_workbook
from app.importers.sheet_classifier import classify_sheet


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
