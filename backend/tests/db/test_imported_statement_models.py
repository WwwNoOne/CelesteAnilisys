from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.enums import StatementImportStatus
from app.models import (
    Account,
    AccountBalance,
    Company,
    FinancialImport,
    ImportedStatement,
    ImportRow,
    Period,
)


def build_database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine


def test_import_keeps_independent_statements_and_candidate_coordinates():
    engine = build_database()

    with Session(engine) as session:
        company = Company(name="Empresa")
        session.add(company)
        session.flush()
        job = FinancialImport(company_id=company.id, period_id=None, file_name="estados.xlsx")
        session.add(job)
        session.flush()
        balance = ImportedStatement(
            source_import_id=job.id,
            sheet_name="Balance 2024",
            source_order=0,
            statement_type="ESTADO_SITUACION_FINANCIERA",
        )
        results = ImportedStatement(
            source_import_id=job.id,
            sheet_name="Resultados 2024",
            source_order=1,
            statement_type="ESTADO_RESULTADOS",
        )
        session.add_all([balance, results])
        session.flush()
        left = ImportRow(
            source_import_id=job.id,
            imported_statement_id=balance.id,
            source_sheet="Balance 2024",
            source_row=8,
            source_text_column=0,
            source_amount_column=1,
            original_name="EFECTIVO",
            ending_balance=Decimal(100),
        )
        right = ImportRow(
            source_import_id=job.id,
            imported_statement_id=balance.id,
            source_sheet="Balance 2024",
            source_row=8,
            source_text_column=4,
            source_amount_column=5,
            original_name="CUENTAS POR PAGAR",
            ending_balance=Decimal(75),
        )
        session.add_all([left, right])
        session.commit()

        assert [item.sheet_name for item in job.statements] == ["Balance 2024", "Resultados 2024"]
        assert {(row.source_text_column, row.source_amount_column) for row in balance.rows} == {
            (0, 1),
            (4, 5),
        }


def test_statement_name_is_unique_inside_an_import():
    engine = build_database()

    with Session(engine) as session:
        company = Company(name="Empresa")
        session.add(company)
        session.flush()
        job = FinancialImport(company_id=company.id, period_id=None, file_name="estados.xlsx")
        session.add(job)
        session.flush()
        session.add_all(
            [
                ImportedStatement(source_import_id=job.id, sheet_name="2024", source_order=0),
                ImportedStatement(source_import_id=job.id, sheet_name="2024", source_order=1),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_approved_statement_keeps_period_and_balance_provenance():
    engine = build_database()

    with Session(engine) as session:
        company = Company(name="Empresa")
        period = Period(label="2024", year=2024, as_of_date=date(2024, 12, 31))
        session.add_all([company, period])
        session.flush()
        account = Account(company_id=company.id, code="1101", name="Efectivo")
        job = FinancialImport(company_id=company.id, period_id=None, file_name="estados.xlsx")
        session.add_all([account, job])
        session.flush()
        statement = ImportedStatement(
            source_import_id=job.id,
            sheet_name="Balance",
            source_order=0,
            period_id=period.id,
            status=StatementImportStatus.APPROVED,
            approved_at=date(2026, 9, 22),
        )
        session.add(statement)
        session.flush()
        saved_balance = AccountBalance(
            company_id=company.id,
            period_id=period.id,
            account_id=account.id,
            source_import_id=job.id,
            imported_statement_id=statement.id,
            ending_balance=Decimal("100.00"),
            source_sheet="Balance",
            source_row=8,
        )
        session.add(saved_balance)
        session.commit()

        assert statement.period is period
        assert saved_balance.imported_statement is statement
        assert statement.balances == [saved_balance]
