from pathlib import Path
from typing import Any

import pandas as pd

from app.schemas.import_analysis import SheetSnapshot, WorkbookSnapshot

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}


def read_workbook(path: Path) -> WorkbookSnapshot:
    """Read workbook values without changing the source file or importing data."""
    path = Path(path)
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Formato no soportado: {extension or '<sin extensión>'}. Use {supported}.")
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    workbook = pd.ExcelFile(path, engine="openpyxl")
    sheets = [
        SheetSnapshot(name=sheet_name, rows=_dataframe_to_rows(workbook.parse(sheet_name, header=None)))
        for sheet_name in workbook.sheet_names
    ]
    return WorkbookSnapshot(path=path, sheets=sheets)


def _dataframe_to_rows(dataframe: pd.DataFrame) -> list[list[Any]]:
    values = dataframe.astype(object).where(dataframe.notna(), None).values.tolist()
    return [list(row) for row in values]
