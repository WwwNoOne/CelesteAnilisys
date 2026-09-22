from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import AccountType, ImportStatus
from app.models import Account, AccountBalance, FinancialImport, Period
from app.schemas.comparison_api import (
    ComparisonGroupResponse,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonRowResponse,
    ComparisonSourceResponse,
    ComparisonStatementResponse,
)
from app.services.catalog_hierarchy_service import get_account_hierarchy_info

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
GROUP_LABELS = {
    "ACTIVO_CORRIENTE": "Activo corriente",
    "ACTIVO_NO_CORRIENTE": "Activo no corriente",
    "TOTAL_ACTIVO": "Total activo",
    "PASIVO_CORRIENTE": "Pasivo corriente",
    "PASIVO_NO_CORRIENTE": "Pasivo no corriente",
    "TOTAL_PASIVO": "Total pasivo",
    "PATRIMONIO": "Patrimonio",
    "TOTAL_PASIVO_PATRIMONIO": "Total pasivo y patrimonio",
    "INGRESOS": "Ingresos",
    "COSTOS": "Costos",
    "GASTOS": "Gastos",
    "OTROS_RESULTADOS": "Otros resultados",
    "IMPUESTOS": "Impuestos",
    "RESULTADOS": "Resultados",
    "SIN_CLASIFICAR": "Sin clasificar",
}
BALANCE_GROUP_ORDER = (
    "ACTIVO_CORRIENTE",
    "ACTIVO_NO_CORRIENTE",
    "TOTAL_ACTIVO",
    "PASIVO_CORRIENTE",
    "PASIVO_NO_CORRIENTE",
    "TOTAL_PASIVO",
    "PATRIMONIO",
    "TOTAL_PASIVO_PATRIMONIO",
    "SIN_CLASIFICAR",
)
RESULTS_GROUP_ORDER = (
    "INGRESOS",
    "COSTOS",
    "GASTOS",
    "OTROS_RESULTADOS",
    "IMPUESTOS",
    "RESULTADOS",
    "SIN_CLASIFICAR",
)


@dataclass(frozen=True, slots=True)
class ChangeResult:
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    change_status: str


@dataclass(frozen=True, slots=True)
class BalanceRecord:
    account: Account
    value: Decimal | None
    source: ComparisonSourceResponse


@dataclass(slots=True)
class AccountNode:
    account: Account
    base_record: BalanceRecord | None = None
    comparison_record: BalanceRecord | None = None
    children: list["AccountNode"] | None = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []

    @property
    def base_value(self) -> Decimal | None:
        return self.base_record.value if self.base_record else None

    @property
    def comparison_value(self) -> Decimal | None:
        return self.comparison_record.value if self.comparison_record else None


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


def compare_statements(
    db: Session,
    company_id: int,
    request: ComparisonRequest,
) -> ComparisonResponse:
    statement_type = normalize_statement_type(request.statement_type)
    available = list_available_statements(db, company_id)
    statements_by_id = {item.period_id: item for item in available}
    base = statements_by_id.get(request.base_period_id)
    comparison = statements_by_id.get(request.comparison_period_id)
    if base is None or comparison is None:
        raise ValueError("Uno de los estados no está disponible para esta empresa")

    warnings = validate_statement_pair(base, comparison, statement_type)
    base_records = _load_period_balances(db, company_id, base.period_id)
    comparison_records = _load_period_balances(db, company_id, comparison.period_id)
    groups = _build_groups(base_records, comparison_records, statement_type)
    return ComparisonResponse(
        statement_type=statement_type,
        base_statement=base,
        comparison_statement=comparison,
        warnings=warnings,
        groups=groups,
    )


def _load_period_balances(
    db: Session,
    company_id: int,
    period_id: int,
) -> dict[int, BalanceRecord]:
    rows = (
        db.query(AccountBalance, Account)
        .join(Account, Account.id == AccountBalance.account_id)
        .join(FinancialImport, FinancialImport.id == AccountBalance.source_import_id)
        .filter(
            AccountBalance.company_id == company_id,
            Account.company_id == company_id,
            AccountBalance.period_id == period_id,
            FinancialImport.company_id == company_id,
            FinancialImport.status == ImportStatus.APPROVED,
        )
        .all()
    )
    return {
        account.id: BalanceRecord(
            account=account,
            value=balance.ending_balance,
            source=ComparisonSourceResponse(
                import_id=balance.source_import_id,
                sheet_name=balance.source_sheet,
                source_row=balance.source_row,
            ),
        )
        for balance, account in rows
    }


def _build_groups(
    base_records: dict[int, BalanceRecord],
    comparison_records: dict[int, BalanceRecord],
    statement_type: str,
) -> list[ComparisonGroupResponse]:
    account_ids = set(base_records) | set(comparison_records)
    nodes = {
        account_id: AccountNode(
            account=(base_records.get(account_id) or comparison_records[account_id]).account,
            base_record=base_records.get(account_id),
            comparison_record=comparison_records.get(account_id),
        )
        for account_id in account_ids
    }
    nodes_by_code = {node.account.code: node for node in nodes.values()}
    roots_by_group: dict[str, list[AccountNode]] = {}
    for node in nodes.values():
        group_key = _account_group_key(node.account, statement_type)
        parent = nodes_by_code.get(node.account.parent_code or "")
        if parent is not None and _account_group_key(parent.account, statement_type) == group_key:
            assert parent.children is not None
            parent.children.append(node)
        else:
            roots_by_group.setdefault(group_key, []).append(node)

    for roots in roots_by_group.values():
        roots.sort(key=lambda item: item.account.code)
        for root in roots:
            _sort_node_children(root)

    base_groups = {
        key: _group_response(key, roots)
        for key, roots in roots_by_group.items()
    }
    if statement_type == "BALANCE_GENERAL":
        base_groups["TOTAL_ACTIVO"] = _derived_group(
            "TOTAL_ACTIVO",
            [base_groups.get("ACTIVO_CORRIENTE"), base_groups.get("ACTIVO_NO_CORRIENTE")],
        )
        base_groups["TOTAL_PASIVO"] = _derived_group(
            "TOTAL_PASIVO",
            [base_groups.get("PASIVO_CORRIENTE"), base_groups.get("PASIVO_NO_CORRIENTE")],
        )
        base_groups["TOTAL_PASIVO_PATRIMONIO"] = _derived_group(
            "TOTAL_PASIVO_PATRIMONIO",
            [base_groups.get("TOTAL_PASIVO"), base_groups.get("PATRIMONIO")],
        )
        order = BALANCE_GROUP_ORDER
    else:
        order = RESULTS_GROUP_ORDER
    return [base_groups[key] for key in order if key in base_groups]


def _group_response(key: str, roots: list[AccountNode]) -> ComparisonGroupResponse:
    base_value = _sum_available([_authoritative_value(root, "base") for root in roots])
    comparison_value = _sum_available(
        [_authoritative_value(root, "comparison") for root in roots]
    )
    change = calculate_change(
        base_value,
        comparison_value,
        base_present=base_value is not None,
        comparison_present=comparison_value is not None,
    )
    return ComparisonGroupResponse(
        key=key,
        name=GROUP_LABELS[key],
        base_value=base_value,
        comparison_value=comparison_value,
        absolute_change=change.absolute_change,
        percentage_change=change.percentage_change,
        change_status=change.change_status,
        children=[_node_response(root, level=1) for root in roots],
    )


def _derived_group(
    key: str,
    source_groups: list[ComparisonGroupResponse | None],
) -> ComparisonGroupResponse:
    present = [group for group in source_groups if group is not None]
    base_value = _sum_available([group.base_value for group in present])
    comparison_value = _sum_available([group.comparison_value for group in present])
    change = calculate_change(
        base_value,
        comparison_value,
        base_present=base_value is not None,
        comparison_present=comparison_value is not None,
    )
    return ComparisonGroupResponse(
        key=key,
        name=GROUP_LABELS[key],
        base_value=base_value,
        comparison_value=comparison_value,
        absolute_change=change.absolute_change,
        percentage_change=change.percentage_change,
        change_status=change.change_status,
    )


def _node_response(node: AccountNode, *, level: int) -> ComparisonRowResponse:
    change = calculate_change(
        node.base_value,
        node.comparison_value,
        base_present=node.base_record is not None,
        comparison_present=node.comparison_record is not None,
    )
    children = node.children or []
    return ComparisonRowResponse(
        key=f"account-{node.account.id}",
        account_id=node.account.id,
        code=node.account.code,
        name=node.account.name,
        level=level,
        base_value=node.base_value,
        comparison_value=node.comparison_value,
        absolute_change=change.absolute_change,
        percentage_change=change.percentage_change,
        change_status=change.change_status,
        base_source=node.base_record.source if node.base_record else None,
        comparison_source=(
            node.comparison_record.source if node.comparison_record else None
        ),
        children=[_node_response(child, level=level + 1) for child in children],
    )


def _authoritative_value(node: AccountNode, side: str) -> Decimal | None:
    own = node.base_value if side == "base" else node.comparison_value
    if own is not None:
        return own
    children = node.children or []
    return _sum_available([_authoritative_value(child, side) for child in children])


def _sum_available(values: list[Decimal | None]) -> Decimal | None:
    available = [value for value in values if value is not None]
    return sum(available, Decimal(0)) if available else None


def _sort_node_children(node: AccountNode) -> None:
    if node.children is None:
        return
    node.children.sort(key=lambda item: item.account.code)
    for child in node.children:
        _sort_node_children(child)


def _account_group_key(account: Account, statement_type: str) -> str:
    info = get_account_hierarchy_info(account)
    path = info["hierarchy_path"].upper()
    account_type = account.account_type
    if statement_type == "BALANCE_GENERAL":
        if account_type == AccountType.ACTIVO:
            return "ACTIVO_NO_CORRIENTE" if "NO CORRIENTE" in path else "ACTIVO_CORRIENTE"
        if account_type == AccountType.PASIVO:
            return "PASIVO_NO_CORRIENTE" if "NO CORRIENTE" in path else "PASIVO_CORRIENTE"
        if account_type == AccountType.PATRIMONIO:
            return "PATRIMONIO"
        return "SIN_CLASIFICAR"

    category = info["category"].upper()
    if category == "INGRESOS":
        return "INGRESOS"
    if category == "COSTOS":
        return "COSTOS"
    if category == "GASTOS":
        return "GASTOS"
    if category == "OTROS INGRESOS/GASTOS":
        return "OTROS_RESULTADOS"
    if category == "IMPUESTOS":
        return "IMPUESTOS"
    if category == "RESULTADOS":
        return "RESULTADOS"
    return "SIN_CLASIFICAR"


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
