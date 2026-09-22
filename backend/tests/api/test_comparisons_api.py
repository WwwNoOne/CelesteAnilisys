from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import AccountType, ImportStatus
from app.models import Account, AccountBalance, Company, FinancialImport, Period
from tests.conftest import client, seed_test_db, test_engine


def setup_function():
    seed_test_db()


def seed_api_comparison_data() -> None:
    with Session(test_engine) as session:
        session.add(Company(id=2, name="Otra empresa"))
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
                Period(
                    id=88,
                    label="Otra empresa 2026",
                    year=2026,
                    statement_type="BALANCE_GENERAL",
                    as_of_date=date(2026, 12, 31),
                ),
                Account(
                    id=601,
                    company_id=1,
                    code="1201",
                    name="Propiedad, Planta y Equipo",
                    account_type=AccountType.ACTIVO,
                ),
                Account(
                    id=701,
                    company_id=2,
                    code="1201",
                    name="Propiedad, Planta y Equipo",
                    account_type=AccountType.ACTIVO,
                ),
            ]
        )
        session.add_all(
            [
                FinancialImport(
                    id=3030,
                    company_id=1,
                    period_id=30,
                    file_name="balance-2024.xlsx",
                    status=ImportStatus.APPROVED,
                ),
                FinancialImport(
                    id=3031,
                    company_id=1,
                    period_id=31,
                    file_name="balance-2025.xlsx",
                    status=ImportStatus.APPROVED,
                ),
                FinancialImport(
                    id=3088,
                    company_id=2,
                    period_id=88,
                    file_name="otra-empresa.xlsx",
                    status=ImportStatus.APPROVED,
                ),
            ]
        )
        session.add_all(
            [
                AccountBalance(
                    company_id=1,
                    period_id=30,
                    account_id=601,
                    source_import_id=3030,
                    ending_balance=Decimal(1000),
                    source_sheet="Balance",
                    source_row=10,
                ),
                AccountBalance(
                    company_id=1,
                    period_id=31,
                    account_id=601,
                    source_import_id=3031,
                    ending_balance=Decimal(1200),
                    source_sheet="Balance",
                    source_row=10,
                ),
                AccountBalance(
                    company_id=2,
                    period_id=88,
                    account_id=701,
                    source_import_id=3088,
                    ending_balance=Decimal(500),
                    source_sheet="Balance",
                    source_row=10,
                ),
            ]
        )
        session.commit()


def test_lists_only_approved_company_statements():
    seed_api_comparison_data()

    response = client.get(
        "/api/companies/1/comparison-statements?statement_type=BALANCE_GENERAL"
    )

    assert response.status_code == 200
    assert [item["period_id"] for item in response.json()] == [31, 30]


def test_compares_two_approved_periods():
    seed_api_comparison_data()

    response = client.post(
        "/api/companies/1/comparisons",
        json={
            "statement_type": "BALANCE_GENERAL",
            "base_period_id": 30,
            "comparison_period_id": 31,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["base_statement"]["period_id"] == 30
    assert body["comparison_statement"]["period_id"] == 31
    assert body["groups"][0]["children"][0]["account_id"] == 601


def test_rejects_cross_company_statement_id():
    seed_api_comparison_data()

    response = client.post(
        "/api/companies/1/comparisons",
        json={
            "statement_type": "BALANCE_GENERAL",
            "base_period_id": 30,
            "comparison_period_id": 88,
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Uno de los estados no está disponible para esta empresa"
    )
