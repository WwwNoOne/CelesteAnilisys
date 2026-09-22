import shutil
from decimal import Decimal
from pathlib import Path

from app.importers.excel_reader import read_workbook
from app.importers.header_detector import detect_header
from app.services.account_extraction_service import extract_account_candidates


def test_bengala_extracts_both_years_with_declared_lines(tmp_path: Path):
    source = Path("data/examples/2025-ER BENGALA.xlsx")
    copied = tmp_path / source.name
    shutil.copy2(source, copied)

    workbook = read_workbook(copied)
    assert {sheet.name for sheet in workbook.sheets} == {"2024", "2025"}

    extracted = {
        sheet.name: extract_account_candidates(sheet, detect_header(sheet.rows))
        for sheet in workbook.sheets
    }
    by_name = {candidate.name: candidate for candidate in extracted["2024"]}

    assert by_name["INGRESOS POR SERVICIOS"].ending_balance == Decimal("12000.00")
    assert all(candidate.ending_balance is not None for candidate in extracted["2024"])
