from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus
from app.models import AccountBalance, FinancialImport, Period
from app.schemas.comparison_api import ComparisonStatementResponse

BALANCE_TYPES = {"BALANCE_GENERAL", "ESTADO_SITUACION_FINANCIERA"}
RESULTS_TYPE = "ESTADO_RESULTADOS"
DIFFERENT_DURATION_WARNING = (
    "Los períodos seleccionados tienen diferente duración. "
    "La comparación porcentual puede no ser directamente equivalente."
)
MONTH_NAMES = (
    "",
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)


@dataclass(frozen=True, slots=True)
class ChangeResult:
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    change_status: str


def calculate_change(
    base_value: Decimal | None,
    comparison_value: Decimal | None,
    *,
    base_present: bool = True,
    comparison_present: bool = True,
) -> ChangeResult:
    if not base_present:
        return ChangeResult(comparison_value, None, "NEW")
    if not comparison_present:
        absolute = -base_value if base_value is not None else None
        return ChangeResult(absolute, None, "REMOVED")
    if base_value is None or comparison_value is None:
        return ChangeResult(None, None, "NO_BASE")

    absolute = comparison_value - base_value
    if base_value == 0:
        status = "UNCHANGED" if comparison_value == 0 else "NEW"
        return ChangeResult(absolute, None, status)

    percentage = (absolute / abs(base_value)) * Decimal(100)
    return ChangeResult(absolute, percentage, "CALCULATED")


def normalize_statement_type(value: str | None) -> str:
    if value in BALANCE_TYPES:
        return "BALANCE_GENERAL"
    if value == RESULTS_TYPE:
        return value
    raise ValueError("Tipo de estado financiero no soportado")


def list_available_statements(
    db: Session,
    company_id: int,
    statement_type: str | None = None,
) -> list[ComparisonStatementResponse]:
    normalized_filter = normalize_statement_type(statement_type) if statement_type else None
    periods = (
        db.query(Period)
        .join(AccountBalance, AccountBalance.period_id == Period.id)
        .join(FinancialImport, FinancialImport.id == AccountBalance.source_import_id)
        .filter(
            AccountBalance.company_id == company_id,
            FinancialImport.company_id == company_id,
            FinancialImport.status == ImportStatus.APPROVED,
        )
        .distinct()
        .all()
    )

    statements: list[ComparisonStatementResponse] = []
    for period in periods:
        try:
            item = _statement_response(period)
        except ValueError:
            continue
        if normalized_filter is None or item.statement_type == normalized_filter:
            statements.append(item)
    return sorted(statements, key=_statement_sort_key, reverse=True)


def validate_statement_pair(
    base: ComparisonStatementResponse,
    comparison: ComparisonStatementResponse,
    requested_type: str,
) -> list[str]:
    normalized_requested = normalize_statement_type(requested_type)
    if base.period_id == comparison.period_id:
        raise ValueError("No se puede comparar el mismo estado financiero")
    if (
        base.statement_type != comparison.statement_type
        or base.statement_type != normalized_requested
    ):
        raise ValueError("Los estados seleccionados tienen tipos diferentes")

    if normalized_requested == "BALANCE_GENERAL":
        if base.as_of_date is None or comparison.as_of_date is None:
            raise ValueError("Los balances seleccionados no tienen fecha de corte completa")
        if base.as_of_date >= comparison.as_of_date:
            raise ValueError("El período base debe ser anterior al período comparado")
        return []

    if (
        base.period_start is None
        or base.period_end is None
        or comparison.period_start is None
        or comparison.period_end is None
    ):
        raise ValueError("Los estados de resultados no tienen intervalos completos")
    if (base.period_start, base.period_end) >= (
        comparison.period_start,
        comparison.period_end,
    ):
        raise ValueError("El período base debe ser anterior al período comparado")
    if base.duration_days != comparison.duration_days:
        return [DIFFERENT_DURATION_WARNING]
    return []


def _statement_response(period: Period) -> ComparisonStatementResponse:
    statement_type = normalize_statement_type(period.statement_type)
    duration_days = None
    if period.period_start is not None and period.period_end is not None:
        duration_days = (period.period_end - period.period_start).days + 1
    return ComparisonStatementResponse(
        period_id=period.id,
        statement_type=statement_type,
        label=_statement_label(period, statement_type),
        as_of_date=period.as_of_date,
        period_start=period.period_start,
        period_end=period.period_end,
        duration_days=duration_days,
    )


def _statement_label(period: Period, statement_type: str) -> str:
    if statement_type == "BALANCE_GENERAL" and period.as_of_date is not None:
        return _format_date(period.as_of_date, include_year=True)
    if period.period_start is not None and period.period_end is not None:
        if period.period_start.year == period.period_end.year:
            start = _format_date(period.period_start, include_year=False)
            end = _format_date(period.period_end, include_year=False)
            return f"{period.period_end.year} · {start} — {end}"
        start = _format_date(period.period_start, include_year=True)
        end = _format_date(period.period_end, include_year=True)
        return f"{start} — {end}"
    return period.label


def _format_date(value: date, *, include_year: bool) -> str:
    formatted = f"{value.day:02d} {MONTH_NAMES[value.month]}"
    return f"{formatted} {value.year}" if include_year else formatted


def _statement_sort_key(item: ComparisonStatementResponse) -> date:
    return item.as_of_date or item.period_end or date.min
