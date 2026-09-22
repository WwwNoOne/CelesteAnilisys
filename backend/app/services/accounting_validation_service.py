from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import CanonicalRole, ValidationStatus
from app.models import Account, FinancialImport, ImportRow
from app.schemas.accounting_validation import (
    AccountingComponent,
    AccountingRuleResult,
    AccountingSource,
    AccountingValidationResponse,
)

TOLERANCE = Decimal("0.01")


def _rule(
    rule_id: str,
    label: str,
    components: dict[CanonicalRole, AccountingComponent],
    required: list[CanonicalRole],
    left_value: Decimal | None,
    right_value: Decimal | None,
) -> AccountingRuleResult:
    missing = [role for role in required if role not in components or not components[role].explicit]
    sources = [source for role in required if role in components for source in components[role].sources]
    row_ids = sorted({row_id for role in required if role in components for row_id in components[role].row_ids})
    if missing:
        return AccountingRuleResult(
            rule_id=rule_id,
            label=label,
            status=ValidationStatus.MISSING_COMPONENTS,
            left_value=None,
            right_value=None,
            difference=None,
            missing_roles=missing,
            row_ids=row_ids,
            sources=sources,
        )

    assert left_value is not None and right_value is not None
    difference = left_value - right_value
    return AccountingRuleResult(
        rule_id=rule_id,
        label=label,
        status=(
            ValidationStatus.VALID
            if abs(difference) <= TOLERANCE
            else ValidationStatus.MISMATCH
        ),
        left_value=left_value,
        right_value=right_value,
        difference=difference,
        row_ids=row_ids,
        sources=sources,
    )


def has_blocking_rules(validation: AccountingValidationResponse) -> bool:
    return any(
        rule.status in (ValidationStatus.MISMATCH, ValidationStatus.DUPLICATE_CONFLICT)
        for rule in validation.rules
    )


def validate_balance_equation(
    components: dict[CanonicalRole, AccountingComponent],
) -> AccountingRuleResult:
    required = [CanonicalRole.ACTIVO, CanonicalRole.PASIVO, CanonicalRole.PATRIMONIO]
    complete = all(role in components and components[role].explicit for role in required)
    left = components[CanonicalRole.ACTIVO].value if complete else None
    right = (
        components[CanonicalRole.PASIVO].value + components[CanonicalRole.PATRIMONIO].value
        if complete
        else None
    )
    return _rule("balance", "Activo = Pasivo + Patrimonio", components, required, left, right)


def validate_income_statement_equations(
    components: dict[CanonicalRole, AccountingComponent],
) -> list[AccountingRuleResult]:
    gross_roles = [
        CanonicalRole.VENTAS,
        CanonicalRole.COSTO_VENTAS,
        CanonicalRole.UTILIDAD_BRUTA,
    ]
    gross_complete = all(role in components and components[role].explicit for role in gross_roles)
    gross = _rule(
        "gross_profit",
        "Ventas - Costo de ventas = Utilidad bruta",
        components,
        gross_roles,
        components[CanonicalRole.VENTAS].value - components[CanonicalRole.COSTO_VENTAS].value
        if gross_complete
        else None,
        components[CanonicalRole.UTILIDAD_BRUTA].value if gross_complete else None,
    )

    result_roles = [
        CanonicalRole.UTILIDAD_BRUTA,
        CanonicalRole.RESULTADO_EJERCICIO,
        CanonicalRole.GASTOS,
        CanonicalRole.IMPUESTOS,
    ]
    result_complete = all(role in components and components[role].explicit for role in result_roles)
    result = _rule(
        "net_result",
        "Utilidad bruta = Resultado + Gastos + Impuestos",
        components,
        result_roles,
        components[CanonicalRole.UTILIDAD_BRUTA].value if result_complete else None,
        (
            components[CanonicalRole.RESULTADO_EJERCICIO].value
            + components[CanonicalRole.GASTOS].value
            + components[CanonicalRole.IMPUESTOS].value
            if result_complete
            else None
        ),
    )
    return [gross, result]


def validate_import_accounting(
    db: Session,
    import_id: int,
    sheet_name: str | None = None,
) -> AccountingValidationResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise ValueError("Importación no encontrada")

    rows = (
        db.query(ImportRow, Account)
        .join(Account, ImportRow.matched_account_id == Account.id)
        .filter(
            ImportRow.source_import_id == import_id,
            Account.canonical_role.is_not(None),
        )
    )
    if sheet_name is not None:
        rows = rows.filter(ImportRow.source_sheet == sheet_name)
    rows = rows.order_by(ImportRow.source_sheet, ImportRow.source_row, ImportRow.id).all()

    groups: dict[str, list[tuple[ImportRow, Account]]] = {}
    for row, account in rows:
        groups.setdefault(row.source_sheet, []).append((row, account))

    rules: list[AccountingRuleResult] = []
    balance_roles = {CanonicalRole.ACTIVO, CanonicalRole.PASIVO, CanonicalRole.PATRIMONIO}
    income_roles = set(CanonicalRole) - balance_roles

    for group_rows in groups.values():
        components: dict[CanonicalRole, AccountingComponent] = {}
        sources_by_role: dict[CanonicalRole, list[AccountingSource]] = {}
        for row, account in group_rows:
            role = account.canonical_role
            if role is None or row.ending_balance is None:
                continue
            source = AccountingSource(
                account_id=account.id,
                account_code=account.code,
                account_name=account.name,
                canonical_role=role,
                value=row.ending_balance,
                sheet=row.source_sheet,
                source_row=row.source_row,
                row_id=row.id,
            )
            sources_by_role.setdefault(role, []).append(source)
            if role not in components:
                components[role] = AccountingComponent(
                    value=row.ending_balance,
                    row_ids=[row.id],
                    sources=[source],
                    explicit=True,
                )

        for role, role_sources in sources_by_role.items():
            values = {source.value for source in role_sources}
            if len(values) <= 1:
                continue
            row_ids = sorted(source.row_id for source in role_sources if source.row_id is not None)
            rules.append(
                AccountingRuleResult(
                    rule_id=f"duplicate_{role.value.lower()}",
                    label=f"Declaraciones duplicadas de {role.value}",
                    status=ValidationStatus.DUPLICATE_CONFLICT,
                    left_value=role_sources[0].value,
                    right_value=role_sources[1].value,
                    difference=role_sources[0].value - role_sources[1].value,
                    row_ids=row_ids,
                    sources=role_sources,
                )
            )
        present_roles = set(components)
        if present_roles & balance_roles:
            rules.append(validate_balance_equation(components))
        if present_roles & income_roles:
            rules.extend(validate_income_statement_equations(components))

    return AccountingValidationResponse(
        valid=bool(rules) and all(rule.status == ValidationStatus.VALID for rule in rules),
        rules=rules,
    )
