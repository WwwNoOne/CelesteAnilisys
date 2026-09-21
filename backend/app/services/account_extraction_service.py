from dataclasses import dataclass
from typing import Any

from app.normalizers.text_normalizer import normalize_account_name
from app.schemas.import_analysis import HeaderDetection, SheetSnapshot


@dataclass(slots=True)
class AccountCandidate:
    code: str | None
    name: str
    normalized_name: str
    sheet: str
    excel_row: int
    context_codes: tuple[str, ...] = ()
    is_group: bool = False


def extract_account_candidates(
    sheet: SheetSnapshot,
    header: HeaderDetection,
) -> list[AccountCandidate]:
    if header.row_index is None:
        return []

    candidates: list[AccountCandidate] = []
    for row_index, row in enumerate(sheet.rows[header.row_index + 1 :], start=header.row_index + 2):
        code = _cell_as_string(row, header.columns.get("code"))
        name = _cell_as_string(row, header.columns.get("account_name"))
        if not code and not name:
            continue
        if not name:
            name = code or ""
        candidates.append(
            AccountCandidate(
                code=code,
                name=name,
                normalized_name=normalize_account_name(name),
                sheet=sheet.name,
                excel_row=row_index,
                is_group=bool(code and not _has_amount(row, header)),
            )
        )
    return candidates


def _cell_as_string(row: list[Any], index: int | None) -> str | None:
    if index is None or index >= len(row) or row[index] is None:
        return None
    value = str(row[index]).strip()
    return value or None


def _has_amount(row: list[Any], header: HeaderDetection) -> bool:
    amount_fields = ("opening_balance", "debits", "credits", "ending_balance")
    return any(
        field in header.columns
        and header.columns[field] < len(row)
        and row[header.columns[field]] not in (None, "")
        for field in amount_fields
    )
