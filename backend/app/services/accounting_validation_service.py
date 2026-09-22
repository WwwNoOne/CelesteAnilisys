from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import RowClassification, ValidationStatus
from app.models import FinancialImport, ImportRow
from app.schemas.accounting_validation import (
    AccountingRuleResult,
    AccountingValidationResponse,
)

TOLERANCE = Decimal("0.01")


def _rollup_rule(
    rule_id: str,
    label: str,
    declared: Decimal,
    computed: Decimal,
    row_ids: list[int],
) -> AccountingRuleResult:
    difference = declared - computed
    return AccountingRuleResult(
        rule_id=rule_id,
        label=label,
        status=(
            ValidationStatus.VALID
            if abs(difference) <= TOLERANCE
            else ValidationStatus.MISMATCH
        ),
        left_value=declared,
        right_value=computed,
        difference=difference,
        row_ids=row_ids,
    )


def has_blocking_rules(validation: AccountingValidationResponse) -> bool:
    return any(rule.status == ValidationStatus.MISMATCH for rule in validation.rules)


def _validate_sheet_rollup(rows: list[ImportRow]) -> list[AccountingRuleResult]:
    """Validate the structural roll-up of a sheet.

    - Every TOTAL must equal the sum of the SUBTOTAL lines directly beneath it.
    - The balance equation compares asset totals against liability + equity totals.
    - CUENTA lines are treated as detail and headers (ENCABEZADO) and notes are ignored.
    """
    rules: list[AccountingRuleResult] = []

    section: str | None = None
    subtotal_sum = Decimal(0)
    subtotal_ids: list[int] = []
    section_totals: dict[str, list[tuple[str, Decimal, int]]] = {}

    def flush_total(row: ImportRow, balance: Decimal) -> None:
        nonlocal subtotal_sum, subtotal_ids
        if subtotal_ids:
            rules.append(
                _rollup_rule(
                    f"total_{row.id}",
                    f"Total '{row.original_name}'",
                    balance,
                    subtotal_sum,
                    [row.id, *subtotal_ids],
                )
            )
        subtotal_sum = Decimal(0)
        subtotal_ids = []

    for row in rows:
        cls = row.row_classification
        balance = row.ending_balance or Decimal(0)

        if cls == RowClassification.ENCABEZADO:
            section = row.original_name or ""
            continue

        if cls in (RowClassification.NOTA, RowClassification.IGNORAR):
            continue

        if cls == RowClassification.CUENTA:
            continue

        if cls == RowClassification.SUBTOTAL:
            subtotal_sum += balance
            subtotal_ids.append(row.id)
            continue

        if cls == RowClassification.TOTAL:
            flush_total(row, balance)
            if section is not None:
                section_totals.setdefault(section, []).append(
                    (row.original_name or "", balance, row.id)
                )
            continue

    # Balance equation: assets totals vs liabilities + equity totals.
    assets = Decimal(0)
    equity = Decimal(0)
    balance_row_ids: list[int] = []
    for section_name, totals in section_totals.items():
        upper = section_name.upper()
        for _total_name, total_value, total_id in totals:
            if "ACTIVO" in upper:
                assets += total_value
                balance_row_ids.append(total_id)
            elif "PASIVO" in upper or "PATRIMONIO" in upper:
                equity += total_value
                balance_row_ids.append(total_id)

    if assets or equity:
        rules.append(
            _rollup_rule(
                "balance",
                "Activo = Pasivo + Patrimonio",
                assets,
                equity,
                balance_row_ids,
            )
        )

    return rules


def validate_import_accounting(
    db: Session,
    import_id: int,
    sheet_name: str | None = None,
) -> AccountingValidationResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise ValueError("Importación no encontrada")

    query = db.query(ImportRow).filter(ImportRow.source_import_id == import_id)
    if sheet_name is not None:
        query = query.filter(ImportRow.source_sheet == sheet_name)
    rows = query.order_by(
        ImportRow.source_sheet,
        ImportRow.source_text_column,
        ImportRow.source_row,
        ImportRow.id,
    ).all()

    groups: dict[str, list[ImportRow]] = {}
    for row in rows:
        groups.setdefault(row.source_sheet, []).append(row)

    rules: list[AccountingRuleResult] = []
    for group_rows in groups.values():
        rules.extend(_validate_sheet_rollup(group_rows))

    return AccountingValidationResponse(
        valid=bool(rules) and all(rule.status == ValidationStatus.VALID for rule in rules),
        rules=rules,
    )
