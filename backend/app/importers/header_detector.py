from numbers import Number
from typing import Any

from app.normalizers.text_normalizer import is_metadata_or_signature, normalize_account_name
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
        column_blocks=[best_columns],
    )


def _detect_statement_layout(rows: list[list[Any]]) -> HeaderDetection | None:
    """Detect report-style sheets whose account labels and amounts have no header row."""
    col_counts: dict[int, int] = {}
    for r in rows[:60]:
        for c_idx, val in enumerate(r):
            if isinstance(val, str) and val.strip() and not is_metadata_or_signature(val):
                has_num = any(
                    isinstance(v, Number) and not isinstance(v, bool) for v in r[c_idx + 1 : c_idx + 4]
                )
                normalized = normalize_account_name(val)
                if has_num or normalized in ("ACTIVOS", "PASIVOS", "PATRIMONIO"):
                    col_counts[c_idx] = col_counts.get(c_idx, 0) + 1

    text_cols = [c for c, count in sorted(col_counts.items()) if count >= 2]
    if not text_cols:
        candidate_rows = [
            row
            for row in rows[:60]
            if row
            and isinstance(row[0], str)
            and row[0].strip()
            and any(isinstance(value, Number) and not isinstance(value, bool) for value in row[1:])
        ]
        if len(candidate_rows) < 2:
            return None

        numeric_indexes = [
            index
            for index, value in enumerate(candidate_rows[0])
            if isinstance(value, Number) and not isinstance(value, bool)
        ]
        columns = {"account_name": 0, "ending_balance": numeric_indexes[0] if numeric_indexes else 1}
        return HeaderDetection(
            row_index=-1,
            columns=columns,
            confidence=0.25,
            column_blocks=[columns],
        )

    column_blocks: list[dict[str, int]] = []
    for idx, c_idx in enumerate(text_cols):
        next_c = text_cols[idx + 1] if idx + 1 < len(text_cols) else (len(rows[0]) if rows else c_idx + 4)
        num_col = None
        for r in rows[:60]:
            nums = [
                i
                for i, v in enumerate(r[c_idx + 1 : next_c], start=c_idx + 1)
                if isinstance(v, Number) and not isinstance(v, bool)
            ]
            if nums:
                num_col = nums[0]
                break
        block = {
            "account_name": c_idx,
            "ending_balance": num_col if num_col is not None else c_idx + 1,
            "amount_start": c_idx + 1,
            "amount_end": next_c,
        }
        column_blocks.append(block)

    confidence = round(min(0.85, 0.4 + 0.15 * len(column_blocks)), 2)
    return HeaderDetection(
        row_index=-1,
        columns=column_blocks[0],
        confidence=confidence,
        column_blocks=column_blocks,
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
