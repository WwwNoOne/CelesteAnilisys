from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus
from app.models import Company, FinancialImport
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
