from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus
from app.models import FinancialImport
from tests.conftest import client, seed_test_db, test_engine

EXAMPLE_FILE = Path("data/examples/2025-BG BENGALA.xlsx")


def setup_function():
    seed_test_db()


def test_update_import_period_validates_period():
    with Session(test_engine) as session:
        job = FinancialImport(
            id=10,
            company_id=1,
            period_id=1,
            file_name="test.xlsx",
            status=ImportStatus.READY_FOR_REVIEW,
            period_conflict=True,
            period_validated=False,
        )
        session.add(job)
        session.commit()

    response = client.patch(
        "/api/imports/10/period",
        json={"label": "2025", "year": 2025, "month": 12},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["detected_period_label"] == "2025"
    assert data["detected_period_year"] == 2025
    assert data["detected_period_month"] == 12
    assert data["period_validated"] is True
    assert data["period_conflict"] is False


def test_approve_rejects_unvalidated_or_conflicted_period():
    with Session(test_engine) as session:
        job = FinancialImport(
            id=11,
            company_id=1,
            period_id=1,
            file_name="test.xlsx",
            status=ImportStatus.READY_FOR_REVIEW,
            period_conflict=True,
            period_validated=False,
        )
        session.add(job)
        session.commit()

    response = client.post("/api/imports/11/approve")
    assert response.status_code == 422
    assert "período debe validarse" in response.json()["detail"]


def test_real_workbook_with_multiple_sheet_years_analyzes_sheets_independently():
    response = client.post(
        "/api/imports",
        data={"company_id": "1", "period_id": "1"},
        files={
            "file": (
                EXAMPLE_FILE.name,
                EXAMPLE_FILE.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201
    import_id = response.json()["id"]

    analyzed = client.post(f"/api/imports/{import_id}/analyze")
    assert analyzed.status_code == 200
    result = analyzed.json()
    assert result["status"] == "READY_FOR_REVIEW"

    sheets = client.get(f"/api/imports/{import_id}/sheets").json()["sheets"]
    by_name = {s["sheet_name"]: s for s in sheets}

    # Each sheet is analyzed as its own statement with its own cut-off date
    assert by_name["2024"]["sheet_type"] == "ESTADO_SITUACION_FINANCIERA"
    assert by_name["2024"]["as_of_date"] == "2024-12-31"
    assert by_name["2025"]["sheet_type"] == "ESTADO_SITUACION_FINANCIERA"
    assert by_name["2025"]["as_of_date"] == "2025-12-31"
