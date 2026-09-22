from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus
from app.models import AccountBalance, FinancialImport, Period


@dataclass(slots=True)
class DuplicateCheckResult:
    is_duplicate: bool
    duplicate_reason: str | None = None
    existing_import_id: int | None = None
    existing_period_id: int | None = None


def check_statement_duplicate(
    db: Session,
    company_id: int,
    statement_type: str,
    as_of_date: date | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    exclude_import_id: int | None = None,
) -> DuplicateCheckResult:
    """Check if an approved or existing financial statement exists for this company with the exact temporal bounds.

    Identity rules:
    - Balance / Point in time: company + statement_type + as_of_date
    - Income statement / Flow: company + statement_type + period_start + period_end
    """
    # 1. Check existing AccountBalance records for this exact temporal scope
    if as_of_date is not None and "BALANCE" in statement_type.upper():
        existing_balance = (
            db.query(AccountBalance)
            .join(Period, AccountBalance.period_id == Period.id)
            .filter(
                AccountBalance.company_id == company_id,
                Period.as_of_date == as_of_date,
            )
        )
        if exclude_import_id:
            existing_balance = existing_balance.filter(AccountBalance.source_import_id != exclude_import_id)
        first_b = existing_balance.first()
        if first_b:
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_reason=f"Ya existen saldos registrados para el balance con fecha de corte {as_of_date.strftime('%d/%m/%Y')}",
                existing_import_id=first_b.source_import_id,
                existing_period_id=first_b.period_id,
            )

    if period_start is not None and period_end is not None:
        existing_balance = (
            db.query(AccountBalance)
            .join(Period, AccountBalance.period_id == Period.id)
            .filter(
                AccountBalance.company_id == company_id,
                Period.period_start == period_start,
                Period.period_end == period_end,
            )
        )
        if exclude_import_id:
            existing_balance = existing_balance.filter(AccountBalance.source_import_id != exclude_import_id)
        first_b = existing_balance.first()
        if first_b:
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_reason=(
                    f"Ya existe un Estado de Resultados aprobado para el período "
                    f"{period_start.strftime('%d/%m/%Y')} al {period_end.strftime('%d/%m/%Y')}"
                ),
                existing_import_id=first_b.source_import_id,
                existing_period_id=first_b.period_id,
            )

    # 2. Check FinancialImport records
    if as_of_date is not None and "BALANCE" in statement_type.upper():
        matched_import = (
            db.query(FinancialImport)
            .filter(
                FinancialImport.company_id == company_id,
                FinancialImport.status == ImportStatus.APPROVED,
                FinancialImport.detected_as_of_date == as_of_date,
            )
        )
        if exclude_import_id:
            matched_import = matched_import.filter(FinancialImport.id != exclude_import_id)
        existing = matched_import.first()
        if existing:
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_reason=f"Ya existe un balance general aprobado para la fecha de corte {as_of_date.strftime('%d/%m/%Y')}",
                existing_import_id=existing.id,
                existing_period_id=existing.period_id,
            )

    if period_start is not None and period_end is not None and "RESULTADOS" in statement_type.upper():
        matched_import = (
            db.query(FinancialImport)
            .filter(
                FinancialImport.company_id == company_id,
                FinancialImport.status == ImportStatus.APPROVED,
                FinancialImport.detected_period_start == period_start,
                FinancialImport.detected_period_end == period_end,
            )
        )
        if exclude_import_id:
            matched_import = matched_import.filter(FinancialImport.id != exclude_import_id)
        existing = matched_import.first()
        if existing:
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_reason=(
                    f"Ya existe un Estado de Resultados aprobado para el período "
                    f"{period_start.strftime('%d/%m/%Y')} al {period_end.strftime('%d/%m/%Y')}"
                ),
                existing_import_id=existing.id,
                existing_period_id=existing.period_id,
            )

    return DuplicateCheckResult(is_duplicate=False)
