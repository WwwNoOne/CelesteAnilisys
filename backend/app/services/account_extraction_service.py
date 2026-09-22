import re
from dataclasses import dataclass
from decimal import Decimal
from numbers import Number
from typing import Any

from app.domain.enums import RowClassification
from app.normalizers.text_normalizer import is_metadata_or_signature, normalize_account_name
from app.schemas.import_analysis import HeaderDetection, SheetSnapshot

CODE_NAME_PATTERN = re.compile(r"^(\d+(?:[\.\-]\d+)*)\s+(.+)$")

_ACCOUNTING_GROUPS = {
    "ACTIVO",
    "ACTIVOS",
    "PASIVO",
    "PASIVOS",
    "PATRIMONIO",
    "CORRIENTE",
    "NO CORRIENTE",
    "INGRESOS",
    "INGRESOS DE OPERACION",
    "COSTO DE VENTAS",
    "GASTOS DE OPERACION",
    "GASTOS DE ADMINISTRACION",
    "GASTOS DE VENTAS",
    "TOTAL ACTIVO",
    "TOTAL PASIVO",
    "TOTAL PATRIMONIO",
    "TOTAL PASIVO Y PATRIMONIO",
    "UTILIDAD BRUTA",
    "UTILIDAD DEL EJERCICIO",
    "PERDIDA DEL EJERCICIO",
    "MENOS",
    "MAS",
}


def detect_candidate_classification(normalized_name: str, has_amount: bool) -> RowClassification:
    if normalized_name.startswith("TOTAL ") or normalized_name in (
        "TOTAL", "TOTAL ACTIVO", "TOTAL ACTIVOS", "TOTAL PASIVO", "TOTAL PASIVOS",
        "TOTAL PATRIMONIO", "TOTAL PASIVO Y PATRIMONIO", "TOTAL PASIVOS Y PATRIMONIO",
        "TOTAL INGRESOS", "TOTAL GASTOS", "TOTAL COSTOS",
    ):
        return RowClassification.TOTAL

    if normalized_name.startswith("SUBTOTAL ") or normalized_name in (
        "UTILIDAD BRUTA", "UTILIDAD DE OPERACION", "UTILIDAD DEL EJERCICIO",
        "PERDIDA DEL EJERCICIO", "PERIDA DEL EJERCICO", "CORRIENTE", "NO CORRIENTE",
        "NETO A PAGAR",
    ):
        return RowClassification.SUBTOTAL

    if normalized_name in (
        "ACTIVO", "ACTIVOS", "PASIVO", "PASIVOS", "PATRIMONIO",
        "INGRESOS DE OPERACION", "COSTO DE VENTAS", "GASTOS DE OPERACION",
        "CONCILIACION DE IMPUESTOS", "MENOS", "MAS",
    ):
        return RowClassification.ENCABEZADO

    if (
        normalized_name.startswith(("MAS: ", "MENOS "))
        or "CONCILIACION" in normalized_name
        or "NOTA" in normalized_name
    ):
        return RowClassification.NOTA

    return RowClassification.CUENTA


@dataclass(slots=True)
class AccountCandidate:
    code: str | None
    name: str
    normalized_name: str
    sheet: str
    excel_row: int
    context_codes: tuple[str, ...] = ()
    is_group: bool = False
    row_classification: RowClassification = RowClassification.CUENTA
    opening_balance: Decimal | None = None
    debits: Decimal | None = None
    credits: Decimal | None = None
    ending_balance: Decimal | None = None


def extract_account_candidates(
    sheet: SheetSnapshot,
    header: HeaderDetection,
) -> list[AccountCandidate]:
    if header.row_index is None:
        return []

    candidates: list[AccountCandidate] = []
    blocks = header.column_blocks or ([header.columns] if header.columns else [])
    start_row = max(0, header.row_index + 1)

    for row_offset, row in enumerate(sheet.rows[start_row:]):
        actual_excel_row = start_row + row_offset + 1
        for block in blocks:
            code = _cell_as_string(row, block.get("code"))
            name = _cell_as_string(row, block.get("account_name"))

            if not code and not name:
                continue

            if name and is_metadata_or_signature(name):
                continue

            if not code and name:
                match = CODE_NAME_PATTERN.match(name)
                if match:
                    code = match.group(1)
                    name = match.group(2).strip()

            if not name:
                name = code or ""

            if not name:
                continue

            normalized = normalize_account_name(name)
            has_amount = _has_amount(row, block)

            if header.row_index < 0 and not has_amount and normalized not in _ACCOUNTING_GROUPS:
                continue

            classification = detect_candidate_classification(normalized, has_amount)
            opening_balance = _extract_amount(row, block, "opening_balance")
            debits = _extract_amount(row, block, "debits")
            credits = _extract_amount(row, block, "credits")
            ending_balance = _extract_amount(row, block, "ending_balance")

            candidates.append(
                AccountCandidate(
                    code=code,
                    name=name,
                    normalized_name=normalized,
                    sheet=sheet.name,
                    excel_row=actual_excel_row,
                    is_group=bool(code and not has_amount),
                    row_classification=classification,
                    opening_balance=opening_balance,
                    debits=debits,
                    credits=credits,
                    ending_balance=ending_balance,
                )
            )

    return candidates


def _extract_amount(row: list[Any], block: dict[str, int], field_name: str) -> Decimal | None:
    if field_name in block and block[field_name] < len(row):
        val = row[block[field_name]]
        if isinstance(val, (int, float, Decimal)) and not isinstance(val, bool):
            return Decimal(str(round(float(val), 2)))
    if field_name == "ending_balance" and "amount_start" in block and "amount_end" in block:
        start = block["amount_start"]
        end = block["amount_end"]
        for v in row[start:end]:
            if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
                return Decimal(str(round(float(v), 2)))
    return None


def _cell_as_string(row: list[Any], index: int | None) -> str | None:
    if index is None or index >= len(row) or row[index] is None:
        return None
    value = str(row[index]).strip()
    return value or None


def _has_amount(row: list[Any], block: dict[str, int]) -> bool:
    if "amount_start" in block and "amount_end" in block:
        start = block["amount_start"]
        end = block["amount_end"]
        return any(
            isinstance(v, Number) and not isinstance(v, bool)
            for v in row[start:end]
        )
    amount_fields = ("opening_balance", "debits", "credits", "ending_balance")
    return any(
        field in block
        and block[field] < len(row)
        and row[block[field]] not in (None, "")
        and isinstance(row[block[field]], Number)
        and not isinstance(row[block[field]], bool)
        for field in amount_fields
    )
