from sqlalchemy.orm import Session

from app.domain.enums import AccountType, ImportStatus, MatchType, RowStatus
from app.models import Account, Company, FinancialImport, ImportRow
from tests.conftest import client, seed_test_db, test_engine


def setup_function():
    seed_test_db()
    with Session(test_engine) as session:
        other_company = Company(id=2, name="Otra Empresa")
        session.add(other_company)
        acc1 = Account(id=101, company_id=1, code="1101", name="Efectivo", normalized_name="EFECTIVO", account_type=AccountType.ACTIVO)
        acc2 = Account(id=102, company_id=2, code="1101", name="Efectivo Otra", normalized_name="EFECTIVO OTRA", account_type=AccountType.ACTIVO)
        session.add_all([acc1, acc2])

        job = FinancialImport(
            id=50,
            company_id=1,
            period_id=1,
            file_name="test.xlsx",
            status=ImportStatus.READY_FOR_REVIEW,
            period_validated=True,
            period_conflict=False,
        )
        session.add(job)
        session.flush()

        row1 = ImportRow(
            id=201,
            source_import_id=50,
            source_sheet="2025",
            source_row=8,
            original_name="Efectivo en caja",
            normalized_name="EFECTIVO EN CAJA",
            status=RowStatus.UNKNOWN,
            match_type=MatchType.NONE,
        )
        row2 = ImportRow(
            id=202,
            source_import_id=50,
            source_sheet="2025",
            source_row=9,
            original_name="Fila irrelevante",
            normalized_name="FILA IRRELEVANTE",
            status=RowStatus.UNKNOWN,
            match_type=MatchType.NONE,
        )
        session.add_all([row1, row2])
        session.commit()


def test_search_company_accounts():
    res = client.get("/api/companies/1/accounts?query=efectivo")
    assert res.status_code == 200
    accounts = res.json()
    assert len(accounts) == 1
    assert accounts[0]["id"] == 101
    assert accounts[0]["code"] == "1101"

    # Query for other company should not return company 1 accounts
    res2 = client.get("/api/companies/2/accounts?query=efectivo")
    assert res2.status_code == 200
    accounts2 = res2.json()
    assert len(accounts2) == 1
    assert accounts2[0]["id"] == 102


def test_match_row_to_existing_account():
    res = client.patch(
        "/api/imports/50/rows/201",
        json={"action": "match", "account_id": 101},
    )
    assert res.status_code == 200
    summary = res.json()
    assert summary["recognized_rows"] == 1
    assert summary["review_rows"] == 1  # row 202 is still UNKNOWN
    assert summary["unknown_rows"] == 1

    with Session(test_engine) as session:
        row = session.get(ImportRow, 201)
        assert row.status == RowStatus.MATCHED
        assert row.matched_account_id == 101


def test_reject_matching_account_from_another_company():
    res = client.patch(
        "/api/imports/50/rows/201",
        json={"action": "match", "account_id": 102},  # belongs to company 2
    )
    assert res.status_code == 422
    assert "no pertenece a la empresa" in res.json()["detail"]


def test_ignore_row_and_approve_when_all_resolved():
    # Match row 201
    client.patch("/api/imports/50/rows/201", json={"action": "match", "account_id": 101})

    # Try to approve before resolving row 202 -> must fail
    res_block = client.post("/api/imports/50/approve")
    assert res_block.status_code == 422
    assert "pendientes de revisión" in res_block.json()["detail"]

    # Ignore row 202
    res_ignore = client.patch("/api/imports/50/rows/202", json={"action": "ignore"})
    assert res_ignore.status_code == 200
    summary = res_ignore.json()
    assert summary["review_rows"] == 0
    assert summary["unknown_rows"] == 0

    # Guardar la hoja resuelta antes de finalizar la importación.
    sheet_approval = client.post(
        "/api/imports/50/sheets/2025/approve",
        json={"year": 2025, "statement_type": "ESTADO_RESULTADOS"},
    )
    assert sheet_approval.status_code == 200

    # Now approve must succeed
    res_approve = client.post("/api/imports/50/approve")
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "APPROVED"


def test_classify_row_as_subtotal_or_header_resolves_row():
    # Classify row 202 as SUBTOTAL
    res_classify = client.patch(
        "/api/imports/50/rows/202",
        json={"action": "classify", "row_classification": "SUBTOTAL"},
    )
    assert res_classify.status_code == 200
    with Session(test_engine) as session:
        row = session.get(ImportRow, 202)
        assert row.row_classification.value == "SUBTOTAL"
        assert row.status == RowStatus.MATCHED


def test_accounts_hierarchy_filter_by_statement():
    res = client.get("/api/companies/1/accounts?statement=ESTADO_RESULTADOS")
    assert res.status_code == 200
    accounts = res.json()
    assert len(accounts) > 0
    for acc in accounts:
        assert acc["statement"] == "ESTADO_RESULTADOS"
        assert "Estado de Resultados" in acc["hierarchy_path"]
        assert "category" in acc
