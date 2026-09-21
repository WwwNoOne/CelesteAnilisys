from numbers import Number
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
        fallback = _detect_statement_layout(rows)
        if fallback is not None:
            return fallback
        return HeaderDetection(row_index=None)

    confidence = round(min(1, len(best_columns) / len(_FIELD_KEYWORDS)), 2)
    return HeaderDetection(
        row_index=best_row_index,
        columns=best_columns,
        confidence=confidence,
    )


def _detect_statement_layout(rows: list[list[Any]]) -> HeaderDetection | None:
    """Detect report-style sheets whose account labels and amounts have no header row."""
    candidate_rows = [
        row for row in rows[:60]
        if row and isinstance(row[0], str) and row[0].strip()
        and any(isinstance(value, Number) and not isinstance(value, bool) for value in row[1:])
    ]
    if len(candidate_rows) < 2:
        return None

    numeric_indexes = [
        index for index, value in enumerate(candidate_rows[0])
        if isinstance(value, Number) and not isinstance(value, bool)
    ]
    return HeaderDetection(
        row_index=-1,
        columns={"account_name": 0, "ending_balance": numeric_indexes[0] if numeric_indexes else 1},
        confidence=0.25,
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
