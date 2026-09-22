from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.domain.enums import AccountType, ImportStatus
from app.models import Account, AccountBalance, Company, FinancialImport, Period
from app.schemas.comparison_api import (
    ComparisonRequest,
    ComparisonRowResponse,
    ComparisonStatementResponse,
)
from app.services.comparison_service import (
    calculate_change,
    compare_statements,
    list_available_statements,
    validate_statement_pair,
)
from tests.conftest import seed_test_db, test_engine


def setup_function():
    seed_test_db()


def seed_available_statements(session: Session) -> None:
    session.add(Company(id=2, name="Otra empresa"))
    session.add_all(
        [
            Period(
                id=10,
                label="31 Ene 2025",
                year=2025,
                statement_type="BALANCE_GENERAL",
                as_of_date=date(2025, 1, 31),
            ),
            Period(
                id=11,
                label="31 Dic 2025",
                year=2025,
                statement_type="ESTADO_SITUACION_FINANCIERA",
                as_of_date=date(2025, 12, 31),
            ),
            Period(
                id=12,
                label="2024",
                year=2024,
                statement_type="ESTADO_RESULTADOS",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 12, 31),
            ),
            Period(
                id=13,
                label="2025",
                year=2025,
                statement_type="ESTADO_RESULTADOS",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 9, 30),
            ),
            Period(
                id=99,
                label="2026",
                year=2026,
                statement_type="BALANCE_GENERAL",
                as_of_date=date(2026, 12, 31),
            ),
        ]
    )
    session.add_all(
        [
            Account(
                id=100,
                company_id=1,
                code="1101",
                name="Efectivo",
                account_type=AccountType.ACTIVO,
            ),
            Account(
                id=200,
                company_id=2,
                code="1101",
                name="Efectivo otra empresa",
                account_type=AccountType.ACTIVO,
            ),
        ]
    )

    imports: list[FinancialImport] = []
    balances: list[AccountBalance] = []
    for period_id in (10, 11, 12, 13):
        import_id = 1000 + period_id
        imports.append(
            FinancialImport(
                id=import_id,
                company_id=1,
                period_id=period_id,
                file_name=f"company-1-{period_id}.xlsx",
                status=ImportStatus.APPROVED,
            )
        )
        balances.append(
            AccountBalance(
                company_id=1,
                period_id=period_id,
                account_id=100,
                source_import_id=import_id,
                ending_balance=Decimal(period_id),
                source_sheet="Estado",
                source_row=5,
            )
        )

    imports.extend(
        [
            FinancialImport(
                id=2011,
                company_id=2,
                period_id=11,
                file_name="company-2-11.xlsx",
                status=ImportStatus.APPROVED,
            ),
            FinancialImport(
                id=1099,
                company_id=1,
                period_id=99,
                file_name="pending.xlsx",
                status=ImportStatus.READY_FOR_REVIEW,
            ),
        ]
    )
    balances.extend(
        [
            AccountBalance(
                company_id=2,
                period_id=11,
                account_id=200,
                source_import_id=2011,
                ending_balance=Decimal(20),
                source_sheet="Balance",
                source_row=5,
            ),
            AccountBalance(
                company_id=1,
                period_id=99,
                account_id=100,
                source_import_id=1099,
                ending_balance=Decimal(99),
                source_sheet="Balance",
                source_row=5,
            ),
        ]
    )
    session.add_all(imports)
    session.add_all(balances)
    session.commit()


def statement(
    period_id: int,
    statement_type: str,
    *,
    as_of_date: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> ComparisonStatementResponse:
    return ComparisonStatementResponse(
        period_id=period_id,
        statement_type=statement_type,
        label=str(period_id),
        as_of_date=as_of_date,
        period_start=start,
        period_end=end,
        duration_days=(end - start).days + 1 if start and end else None,
    )


def flatten_rows(rows: list[ComparisonRowResponse]) -> list[ComparisonRowResponse]:
    flattened: list[ComparisonRowResponse] = []
    for row in rows:
        flattened.append(row)
        flattened.extend(flatten_rows(row.children))
    return flattened


def add_approved_import(
    session: Session,
    *,
    import_id: int,
    period_id: int,
    file_name: str,
) -> None:
    session.add(
        FinancialImport(
            id=import_id,
            company_id=1,
            period_id=period_id,
            file_name=file_name,
            status=ImportStatus.APPROVED,
        )
    )


def add_balance(
    session: Session,
    *,
    period_id: int,
    account_id: int,
    import_id: int,
    value: Decimal | None,
    row: int,
) -> None:
    session.add(
        AccountBalance(
            company_id=1,
            period_id=period_id,
            account_id=account_id,
            source_import_id=import_id,
            ending_balance=value,
            source_sheet="Estado",
            source_row=row,
        )
    )


def seed_comparison_pair(session: Session) -> None:
    session.add_all(
        [
            Period(
                id=20,
                label="2024",
                year=2024,
                statement_type="ESTADO_RESULTADOS",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 12, 31),
            ),
            Period(
                id=21,
                label="2025",
                year=2025,
                statement_type="ESTADO_RESULTADOS",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
            ),
            Account(
                id=501,
                company_id=1,
                code="420101",
                name="Gastos de Administración",
                account_type=AccountType.GASTO,
            ),
            Account(
                id=502,
                company_id=1,
                code="5201",
                name="Otros ingresos nuevos",
                account_type=AccountType.INGRESO,
            ),
            Account(
                id=503,
                company_id=1,
                code="4301",
                name="Gastos financieros retirados",
                account_type=AccountType.GASTO,
            ),
        ]
    )
    add_approved_import(session, import_id=3020, period_id=20, file_name="GASTOS.xls")
    add_approved_import(
        session,
        import_id=3021,
        period_id=21,
        file_name="Gastos administrativos.xlsx",
    )
    add_balance(
        session,
        period_id=20,
        account_id=501,
        import_id=3020,
        value=Decimal(100),
        row=10,
    )
    add_balance(
        session,
        period_id=21,
        account_id=501,
        import_id=3021,
        value=Decimal(125),
        row=12,
    )
    add_balance(
        session,
        period_id=21,
        account_id=502,
        import_id=3021,
        value=Decimal(40),
        row=13,
    )
    add_balance(
        session,
        period_id=20,
        account_id=503,
        import_id=3020,
        value=Decimal(50),
        row=14,
    )
    session.commit()


def seed_parent_and_children(session: Session) -> None:
    session.add_all(
        [
            Period(
                id=30,
                label="2024",
                year=2024,
                statement_type="BALANCE_GENERAL",
                as_of_date=date(2024, 12, 31),
            ),
            Period(
                id=31,
                label="2025",
                year=2025,
                statement_type="ESTADO_SITUACION_FINANCIERA",
                as_of_date=date(2025, 12, 31),
            ),
            Account(
                id=601,
                company_id=1,
                code="1201",
                name="Propiedad, Planta y Equipo",
                account_type=AccountType.ACTIVO,
                level=1,
            ),
            Account(
                id=602,
                company_id=1,
                code="120102",
                name="Vehículos",
                account_type=AccountType.ACTIVO,
                level=2,
                parent_code="1201",
            ),
            Account(
                id=603,
                company_id=1,
                code="120104",
                name="Equipo de Computación",
                account_type=AccountType.ACTIVO,
                level=2,
                parent_code="1201",
            ),
        ]
    )
    add_approved_import(session, import_id=3030, period_id=30, file_name="balance-2024.xlsx")
    add_approved_import(session, import_id=3031, period_id=31, file_name="balance-2025.xlsx")
    for period_id, import_id, values in (
        (30, 3030, {601: 1000, 602: 600, 603: 400}),
        (31, 3031, {601: 1200, 602: 700, 603: 500}),
    ):
        for row, (account_id, value) in enumerate(values.items(), start=10):
            add_balance(
                session,
                period_id=period_id,
                account_id=account_id,
                import_id=import_id,
                value=Decimal(value),
                row=row,
            )
    session.commit()


def test_calculate_change_uses_later_minus_base_and_absolute_denominator():
    result = calculate_change(Decimal(-100), Decimal(-75))

    assert result.absolute_change == Decimal(25)
    assert result.percentage_change == Decimal(25)
    assert result.change_status == "CALCULATED"


def test_calculate_change_handles_zero_missing_and_null_without_nan():
    assert calculate_change(Decimal(0), Decimal(10)).change_status == "NEW"
    assert calculate_change(Decimal(0), Decimal(0)).change_status == "UNCHANGED"
    assert calculate_change(None, Decimal(10), base_present=False).change_status == "NEW"
    assert (
        calculate_change(Decimal(10), None, comparison_present=False).change_status
        == "REMOVED"
    )
    assert calculate_change(None, Decimal(10), base_present=True).change_status == "NO_BASE"


def test_list_available_statements_keeps_same_year_dates_separate():
    with Session(test_engine) as session:
        seed_available_statements(session)
        items = list_available_statements(session, 1, "BALANCE_GENERAL")

    assert [item.period_id for item in items] == [11, 10]
    assert [item.as_of_date for item in items] == [
        date(2025, 12, 31),
        date(2025, 1, 31),
    ]


def test_list_available_statements_is_scoped_through_company_balances():
    with Session(test_engine) as session:
        seed_available_statements(session)
        company_one = list_available_statements(session, 1)
        company_two = list_available_statements(session, 2)

    assert {item.period_id for item in company_one} == {10, 11, 12, 13}
    assert {item.period_id for item in company_two} == {11}


def test_unapproved_import_is_not_available():
    with Session(test_engine) as session:
        seed_available_statements(session)
        items = list_available_statements(session, 1)

    assert all(item.period_id != 99 for item in items)


def test_results_with_different_duration_returns_warning():
    base = statement(
        12,
        "ESTADO_RESULTADOS",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
    )
    later = statement(
        13,
        "ESTADO_RESULTADOS",
        start=date(2025, 1, 1),
        end=date(2025, 9, 30),
    )

    warnings = validate_statement_pair(base, later, "ESTADO_RESULTADOS")

    assert warnings == [
        (
            "Los períodos seleccionados tienen diferente duración. "
            "La comparación porcentual puede no ser directamente equivalente."
        )
    ]


def test_validation_rejects_mixed_same_and_reversed_periods():
    balance_2024 = statement(
        20,
        "BALANCE_GENERAL",
        as_of_date=date(2024, 12, 31),
    )
    balance_2025 = statement(
        21,
        "BALANCE_GENERAL",
        as_of_date=date(2025, 12, 31),
    )
    results_2025 = statement(
        22,
        "ESTADO_RESULTADOS",
        start=date(2025, 1, 1),
        end=date(2025, 12, 31),
    )

    with pytest.raises(ValueError, match="mismo estado"):
        validate_statement_pair(balance_2024, balance_2024, "BALANCE_GENERAL")
    with pytest.raises(ValueError, match="tipos diferentes"):
        validate_statement_pair(balance_2024, results_2025, "BALANCE_GENERAL")
    with pytest.raises(ValueError, match="anterior"):
        validate_statement_pair(balance_2025, balance_2024, "BALANCE_GENERAL")


def test_compare_joins_different_source_names_by_account_id():
    with Session(test_engine) as session:
        seed_comparison_pair(session)
        result = compare_statements(
            session,
            1,
            ComparisonRequest(
                statement_type="ESTADO_RESULTADOS",
                base_period_id=20,
                comparison_period_id=21,
            ),
        )

    rows = flatten_rows(result.groups)
    account_rows = [row for row in rows if row.account_id == 501]
    assert len(account_rows) == 1
    assert account_rows[0].base_value == Decimal(100)
    assert account_rows[0].comparison_value == Decimal(125)
    assert account_rows[0].absolute_change == Decimal(25)


def test_compare_marks_accounts_only_present_on_one_side():
    with Session(test_engine) as session:
        seed_comparison_pair(session)
        result = compare_statements(
            session,
            1,
            ComparisonRequest(
                statement_type="ESTADO_RESULTADOS",
                base_period_id=20,
                comparison_period_id=21,
            ),
        )

    rows = flatten_rows(result.groups)
    assert next(row for row in rows if row.account_id == 502).change_status == "NEW"
    assert next(row for row in rows if row.account_id == 503).change_status == "REMOVED"


def test_parent_balance_is_authoritative_when_children_also_have_balances():
    with Session(test_engine) as session:
        seed_parent_and_children(session)
        result = compare_statements(
            session,
            1,
            ComparisonRequest(
                statement_type="BALANCE_GENERAL",
                base_period_id=30,
                comparison_period_id=31,
            ),
        )

    fixed_assets = next(
        group for group in result.groups if group.key == "ACTIVO_NO_CORRIENTE"
    )
    assert fixed_assets.base_value == Decimal(1000)
    assert fixed_assets.comparison_value == Decimal(1200)
    assert fixed_assets.absolute_change == Decimal(200)
    assert len(fixed_assets.children) == 1
    assert len(fixed_assets.children[0].children) == 2
    total_assets = next(group for group in result.groups if group.key == "TOTAL_ACTIVO")
    assert total_assets.base_value == Decimal(1000)
    assert total_assets.comparison_value == Decimal(1200)
