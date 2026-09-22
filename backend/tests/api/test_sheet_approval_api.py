from datetime import date

from sqlalchemy.orm import Session

from app.domain.enums import AccountType, ImportStatus, MatchType, RowClassification, RowStatus
from app.models import Account, AccountBalance, FinancialImport, ImportRow, Period
from tests.conftest import client, seed_test_db, test_engine


def setup_function():
    seed_test_db()
    with Session(test_engine) as session:
        acc1 = Account(
            id=10,
            company_id=1,
            code="5101",
            name="Ingresos por Servicios",
            normalized_name="INGRESOS POR SERVICIOS",
            account_type=AccountType.INGRESO,
        )
        session.add(acc1)

        job = FinancialImport(
            id=80,
            company_id=1,
            period_id=1,
            file_name="bengala.xlsx",
            status=ImportStatus.READY_FOR_REVIEW,
            period_validated=True,
            period_conflict=False,
        )
        session.add(job)
        session.flush()

        row1 = ImportRow(
            id=301,
            source_import_id=80,
            source_sheet="2025",
            source_row=7,
            original_code="5101",
            original_name="Ingresos por Servicios",
            normalized_name="INGRESOS POR SERVICIOS",
            matched_account_id=10,
            match_type=MatchType.EXACT_CODE,
            status=RowStatus.MATCHED,
            row_classification=RowClassification.CUENTA,
            ending_balance=12000,
        )
        row2 = ImportRow(
            id=302,
            source_import_id=80,
            source_sheet="2025",
            source_row=6,
            original_name="INGRESOS DE OPERACION",
            normalized_name="INGRESOS DE OPERACION",
            matched_account_id=None,
            match_type=MatchType.NONE,
            status=RowStatus.MATCHED,
            row_classification=RowClassification.ENCABEZADO,
        )
        session.add_all([row1, row2])
        session.commit()


def test_approve_sheet_persists_account_balances():
    response = client.post(
        "/api/imports/80/sheets/2025/approve",
        json={
            "year": 2025,
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "statement_type": "ESTADO_RESULTADOS",
            "timeframe": "ANNUAL",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["balances_saved"] == 1
    assert data["status"] == "APPROVED"

    with Session(test_engine) as session:
        balance = session.query(AccountBalance).filter(AccountBalance.account_id == 10).first()
        assert balance is not None
        assert float(balance.ending_balance) == 12000.0
        assert balance.source_sheet == "2025"

        # Check created period
        period = session.get(Period, balance.period_id)
        assert period.year == 2025
        assert period.period_start == date(2025, 1, 1)
        assert period.period_end == date(2025, 12, 31)


def test_approve_sheet_warns_on_duplicate():
    # Approve once
    res1 = client.post(
        "/api/imports/80/sheets/2025/approve",
        json={
            "year": 2025,
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "statement_type": "ESTADO_RESULTADOS",
        },
    )
    assert res1.status_code == 200

    # Create another import with the same date bounds
    with Session(test_engine) as session:
        job2 = FinancialImport(
            id=81,
            company_id=1,
            period_id=1,
            file_name="bengala_dup.xlsx",
            status=ImportStatus.READY_FOR_REVIEW,
        )
        session.add(job2)
        row_dup = ImportRow(
            id=303,
            source_import_id=81,
            source_sheet="2025",
            source_row=7,
            original_code="5101",
            original_name="Ingresos por Servicios",
            matched_account_id=10,
            status=RowStatus.MATCHED,
            row_classification=RowClassification.CUENTA,
            ending_balance=15000,
        )
        session.add(row_dup)
        session.commit()

    # Attempt to approve sheet in job2 without overwrite -> duplicate warning
    res_dup = client.post(
        "/api/imports/81/sheets/2025/approve",
        json={
            "year": 2025,
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "statement_type": "ESTADO_RESULTADOS",
            "overwrite": False,
        },
    )
    assert res_dup.status_code == 200
    dup_data = res_dup.json()
    assert dup_data["is_duplicate"] is True
    assert dup_data["success"] is False
    assert "Ya existe un Estado de Resultados" in dup_data["duplicate_warning"]

    # Now approve with overwrite=True -> succeeds and updates balance
    res_over = client.post(
        "/api/imports/81/sheets/2025/approve",
        json={
            "year": 2025,
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "statement_type": "ESTADO_RESULTADOS",
            "overwrite": True,
        },
    )
    assert res_over.status_code == 200
    assert res_over.json()["success"] is True

    with Session(test_engine) as session:
        balance = session.query(AccountBalance).filter(AccountBalance.account_id == 10).first()
        assert float(balance.ending_balance) == 15000.0


def test_import_requires_every_account_sheet_to_be_approved_before_final_approval():
    with Session(test_engine) as session:
        session.add(Account(
            id=11,
            company_id=1,
            code="5102",
            name="Otros ingresos",
            normalized_name="OTROS INGRESOS",
            account_type=AccountType.INGRESO,
        ))
        session.add(ImportRow(
            id=304,
            source_import_id=80,
            source_sheet="2024",
            source_row=7,
            original_code="5102",
            original_name="Otros ingresos",
            normalized_name="OTROS INGRESOS",
            matched_account_id=11,
            match_type=MatchType.EXACT_CODE,
            status=RowStatus.MATCHED,
            row_classification=RowClassification.CUENTA,
            ending_balance=5000,
        ))
        session.commit()

    first_sheet = client.post("/api/imports/80/sheets/2025/approve", json={"year": 2025})
    assert first_sheet.status_code == 200

    with Session(test_engine) as session:
        assert session.get(FinancialImport, 80).status == ImportStatus.READY_FOR_REVIEW

    early_approval = client.post("/api/imports/80/approve")
    assert early_approval.status_code == 422
    assert "hojas" in early_approval.json()["detail"]

    second_sheet = client.post("/api/imports/80/sheets/2024/approve", json={"year": 2024})
    assert second_sheet.status_code == 200

    final_approval = client.post("/api/imports/80/approve")
    assert final_approval.status_code == 200
    assert final_approval.json()["status"] == "APPROVED"
