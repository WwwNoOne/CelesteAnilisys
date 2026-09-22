from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus, MatchType, RowStatus
from app.models import Company, FinancialImport, ImportRow
from tests.conftest import client, seed_test_db, test_engine


def setup_function():
    seed_test_db()
    with Session(test_engine) as session:
        other_company = Company(id=2, name="Otra")
        session.add(other_company)
        job1 = FinancialImport(
            id=61,
            company_id=1,
            period_id=1,
            file_name="balance_2025.xlsx",
            status=ImportStatus.APPROVED,
            detected_period_label="2025",
            detected_period_year=2025,
            period_validated=True,
            total_rows=70,
            recognized_rows=70,
        )
        job2 = FinancialImport(
            id=62,
            company_id=1,
            period_id=1,
            file_name="er_2025.xlsx",
            status=ImportStatus.READY_FOR_REVIEW,
            detected_period_label="2025",
            detected_period_year=2025,
            period_validated=False,
            total_rows=30,
            recognized_rows=25,
            review_rows=5,
            unknown_rows=5,
        )
        job3 = FinancialImport(
            id=63,
            company_id=2,
            period_id=1,
            file_name="otra_import.xlsx",
            status=ImportStatus.UPLOADED,
        )
        session.add_all([job1, job2, job3])
        session.commit()


def test_list_company_imports_filters_by_company_and_returns_summary():
    res = client.get("/api/companies/1/imports")
    assert res.status_code == 200
    imports = res.json()
    assert len(imports) == 2
    ids = [item["id"] for item in imports]
    assert 61 in ids
    assert 62 in ids
    assert 63 not in ids

    # Check that job2 contains unknown_rows and review status
    job2_data = next(item for item in imports if item["id"] == 62)
    assert job2_data["status"] == "READY_FOR_REVIEW"
    assert job2_data["unknown_rows"] == 5
    assert job2_data["review_rows"] == 5


def test_list_company_imports_returns_404_for_unknown_company():
    res = client.get("/api/companies/999/imports")
    assert res.status_code == 404


def test_delete_pending_import_removes_rows_and_stored_file(tmp_path):
    stored_file = tmp_path / "pending.xlsx"
    stored_file.write_bytes(b"test workbook")
    with Session(test_engine) as session:
        pending = session.get(FinancialImport, 62)
        pending.storage_path = str(stored_file)
        session.add(
            ImportRow(
                id=620,
                source_import_id=62,
                source_sheet="Sheet1",
                source_row=1,
                match_type=MatchType.NONE,
                status=RowStatus.UNKNOWN,
            )
        )
        session.commit()

    res = client.delete("/api/imports/62")

    assert res.status_code == 204
    assert not stored_file.exists()
    with Session(test_engine) as session:
        assert session.get(FinancialImport, 62) is None
        assert session.get(ImportRow, 620) is None


def test_delete_import_rejects_approved_financial_statement():
    res = client.delete("/api/imports/61")

    assert res.status_code == 422
    assert res.json()["detail"] == "Solo se pueden eliminar importaciones pendientes de revisión"
    with Session(test_engine) as session:
        assert session.get(FinancialImport, 61) is not None
