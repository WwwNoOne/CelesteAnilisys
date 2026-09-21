from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.enums import AccountType, MatchType, RowStatus
from app.models import Account, AccountBalance, Company, FinancialImport, ImportRow, Period


def test_accounts_keep_leading_zeroes_and_allow_same_name_with_different_codes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        company = Company(name="Empresa de prueba")
        session.add(company)
        session.flush()

        first = Account(
            company_id=company.id,
            code="01",
            name="Honorarios",
            account_type=AccountType.COSTO,
        )
        second = Account(
            company_id=company.id,
            code="420110",
            name="Honorarios",
            account_type=AccountType.GASTO,
        )
        session.add_all([first, second])
        session.commit()

        accounts = session.scalars(select(Account).order_by(Account.code)).all()

    assert [account.code for account in accounts] == ["01", "420110"]
    assert [account.normalized_name for account in accounts] == ["HONORARIOS", "HONORARIOS"]


def test_import_row_keeps_source_traceability_and_balance_is_period_specific():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        company = Company(name="Empresa de prueba")
        period = Period(label="2025", year=2025)
        session.add_all([company, period])
        session.flush()

        account = Account(
            company_id=company.id,
            code="420109",
            name="Papelería y útiles",
            account_type=AccountType.GASTO,
        )
        financial_import = FinancialImport(
            company_id=company.id,
            period_id=period.id,
            file_name="balance.xlsx",
        )
        session.add_all([account, financial_import])
        session.flush()

        row = ImportRow(
            source_import_id=financial_import.id,
            source_sheet="Balance de Comprobación",
            source_row=44,
            original_code="420109",
            original_name="Papelería y útiles",
            normalized_name="PAPELERIA Y UTILES",
            matched_account_id=account.id,
            match_type=MatchType.EXACT_CODE,
            status=RowStatus.MATCHED,
        )
        balance = AccountBalance(
            company_id=company.id,
            period_id=period.id,
            account_id=account.id,
            source_import_id=financial_import.id,
            ending_balance="1250.50",
            source_sheet="Balance de Comprobación",
            source_row=44,
        )
        session.add_all([row, balance])
        session.commit()

        saved_row = session.get(ImportRow, row.id)
        saved_balance = session.get(AccountBalance, balance.id)

    assert saved_row is not None
    assert saved_row.source_row == 44
    assert saved_row.status is RowStatus.MATCHED
    assert saved_balance is not None
    assert str(saved_balance.ending_balance) == "1250.50"
