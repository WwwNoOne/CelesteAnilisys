from typing import Any

from app.normalizers.text_normalizer import normalize_account_name
from app.schemas.import_analysis import HeaderDetection

_FIELD_KEYWORDS: dict[str, tuple[str, ...]] = {
    "code": ("CODIGO DE CUENTA", "CODIGO", "CUENTA CODIGO", "COD"),
    "account_name": ("NOMBRE DE CUENTA", "NOMBRE", "DESCRIPCION", "CUENTA"),
    "opening_balance": ("SALDO ANTERIOR", "SALDO INICIAL", "BALANCE INICIAL"),
    "debits": ("CARGOS", "CARGO", "DEBE", "DEBITOS"),
    "credits": ("ABONOS", "ABONO", "HABER", "CREDITOS"),
    "ending_balance": ("SALDO ACTUAL", "SALDO FINAL", "SALDO"),
}


def detect_header(rows: list[list[Any]]) -> HeaderDetection:
    best_row_index: int | None = None
    best_columns: dict[str, int] = {}

    for row_index, row in enumerate(rows[:60]):
        columns = _detect_columns(row)
        if len(columns) > len(best_columns):
            best_row_index = row_index
            best_columns = columns

    if len(best_columns) < 2:
        return HeaderDetection(row_index=None)

    confidence = round(min(1, len(best_columns) / len(_FIELD_KEYWORDS)), 2)
    return HeaderDetection(
        row_index=best_row_index,
        columns=best_columns,
        confidence=confidence,
    )


def _detect_columns(row: list[Any]) -> dict[str, int]:
    columns: dict[str, int] = {}
    for column_index, value in enumerate(row):
        normalized_value = normalize_account_name(value)
        if not normalized_value:
            continue
        for field_name, keywords in _FIELD_KEYWORDS.items():
            if field_name in columns:
                continue
            if field_name == "account_name" and (
                "CODIGO" in normalized_value or "COD" == normalized_value
            ):
                continue
            if field_name == "ending_balance" and (
                "ANTERIOR" in normalized_value or "INICIAL" in normalized_value
            ):
                continue
            if any(keyword in normalized_value for keyword in keywords):
                columns[field_name] = column_index
    return columns
