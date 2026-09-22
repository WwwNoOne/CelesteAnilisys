from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.domain.enums import CanonicalRole, ValidationStatus
from app.models import Account, AccountBalance, Company, FinancialImport, Period
from app.schemas.accounting_validation import AccountingComponent
from app.services.accounting_validation_service import (
    validate_balance_equation,
    validate_import_accounting,
    validate_income_statement_equations,
)
from tests.conftest import seed_test_db, test_engine


def component(value: str | Decimal, row_id: int = 1) -> AccountingComponent:
    return AccountingComponent(
        value=Decimal(str(value)),
        row_ids=[row_id],
        sources=[],
        explicit=True,
    )


def test_explicit_zero_is_valid_but_missing_component_blocks():
    valid = validate_balance_equation(
        {
            CanonicalRole.ACTIVO: component("100"),
            CanonicalRole.PASIVO: component("0"),
            CanonicalRole.PATRIMONIO: component("100"),
        }
    )
    assert valid.status == ValidationStatus.VALID

    missing = validate_balance_equation(
        {
            CanonicalRole.ACTIVO: component("100"),
            CanonicalRole.PATRIMONIO: component("100"),
        }
    )
    assert missing.status == ValidationStatus.MISSING_COMPONENTS
    assert missing.missing_roles == [CanonicalRole.PASIVO]


@pytest.mark.parametrize("result", [Decimal(20), Decimal(-20)])
def test_income_statement_supports_profit_and_signed_loss(result: Decimal):
    gross = Decimal(100)
    rules = validate_income_statement_equations(
        {
            CanonicalRole.VENTAS: component("150"),
            CanonicalRole.COSTO_VENTAS: component("50"),
            CanonicalRole.UTILIDAD_BRUTA: component(gross),
            CanonicalRole.GASTOS: component(gross - result),
            CanonicalRole.IMPUESTOS: component("0"),
            CanonicalRole.RESULTADO_EJERCICIO: component(result),
        }
    )

    assert all(rule.status == ValidationStatus.VALID for rule in rules)


def test_two_cents_difference_is_mismatch():
    result = validate_balance_equation(
        {
            CanonicalRole.ACTIVO: component("100.02"),
            CanonicalRole.PASIVO: component("60"),
            CanonicalRole.PATRIMONIO: component("40"),
        }
    )

    assert result.status == ValidationStatus.MISMATCH
    assert result.difference == Decimal("0.02")


def test_import_validation_does_not_mix_companies_or_imports():
    seed_test_db()
    with Session(test_engine) as session:
        company_two = Company(id=2, name="Empresa dos")
        period_two = Period(id=2, label="2026", year=2026)
        import_one = FinancialImport(
            id=60,
            company_id=1,
            period_id=1,
            file_name="one.xlsx",
        )
        import_two = FinancialImport(
            id=61,
            company_id=2,
            period_id=2,
            file_name="two.xlsx",
        )
        session.add_all([company_two, period_two, import_one, import_two])
        for account_id, company_id, role in (
            (601, 1, CanonicalRole.ACTIVO),
            (602, 1, CanonicalRole.PASIVO),
            (603, 1, CanonicalRole.PATRIMONIO),
            (611, 2, CanonicalRole.ACTIVO),
        ):
            session.add(
                Account(
                    id=account_id,
                    company_id=company_id,
                    code=str(account_id),
                    name=role.value,
                    canonical_role=role,
                )
            )
        session.flush()
        for account_id, company_id, period_id, import_id, value in (
            (601, 1, 1, 60, "100"),
            (602, 1, 1, 60, "40"),
            (603, 1, 1, 60, "60"),
            (611, 2, 2, 61, "999"),
        ):
            session.add(
                AccountBalance(
                    company_id=company_id,
                    period_id=period_id,
                    account_id=account_id,
                    source_import_id=import_id,
                    ending_balance=Decimal(value),
                    source_sheet="Balance",
                    source_row=account_id,
                    is_authoritative=True,
                )
            )
        session.commit()

        validation = validate_import_accounting(session, 60)

    assert validation.valid is True
    assert {source.account_id for rule in validation.rules for source in rule.sources} == {
        601,
        602,
        603,
    }


def test_conflicting_declarations_for_one_role_block_validation():
    seed_test_db()
    with Session(test_engine) as session:
        job = FinancialImport(id=62, company_id=1, period_id=1, file_name="conflict.xlsx")
        session.add(job)
        values = [
            (621, CanonicalRole.ACTIVO, "100"),
            (622, CanonicalRole.ACTIVO, "110"),
            (623, CanonicalRole.PASIVO, "40"),
            (624, CanonicalRole.PATRIMONIO, "60"),
        ]
        for source_row, (account_id, role, value) in enumerate(values, start=1):
            account = Account(
                id=account_id,
                company_id=1,
                code=str(account_id),
                name=f"{role.value} {account_id}",
                canonical_role=role,
            )
            session.add(account)
            session.flush()
            session.add(
                AccountBalance(
                    company_id=1,
                    period_id=1,
                    account_id=account_id,
                    source_import_id=62,
                    ending_balance=Decimal(value),
                    source_sheet="Balance",
                    source_row=source_row,
                    is_authoritative=True,
                )
            )
        session.commit()

        validation = validate_import_accounting(session, 62)

    assert validation.valid is False
    assert validation.rules[0].status == ValidationStatus.DUPLICATE_CONFLICT
    assert {source.account_id for source in validation.rules[0].sources} == {621, 622}
