from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.main import app
from app.models import Company, Period

EXAMPLE_FILE = Path("data/examples/2025-BG BENGALA.xlsx")
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)


def override_get_db():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_function():
    with Session(engine) as session:
        session.query(Company).delete()
        session.query(Period).delete()
        session.add_all([Company(id=1, name="Bengala"), Period(id=1, label="2025", year=2025)])
        session.commit()


def test_rejects_unsupported_file_extension():
    response = client.post(
        "/api/imports",
        data={"company_id": "1", "period_id": "1"},
        files={"file": ("reporte.pdf", b"not an excel file", "application/pdf")},
    )

    assert response.status_code == 400
    assert "Formato no soportado" in response.json()["detail"]


def test_upload_analyze_and_query_real_workbook():
    response = client.post(
        "/api/imports",
        data={"company_id": "1", "period_id": "1"},
        files={"file": (EXAMPLE_FILE.name, EXAMPLE_FILE.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 201
    import_id = response.json()["id"]
    assert response.json()["status"] == "UPLOADED"

    analysis = client.post(f"/api/imports/{import_id}/analyze")

    assert analysis.status_code == 200
    assert analysis.json()["status"] == "READY_FOR_REVIEW"
    assert analysis.json()["total_rows"] >= 0

    sheets = client.get(f"/api/imports/{import_id}/sheets")
    rows = client.get(f"/api/imports/{import_id}/rows")
    issues = client.get(f"/api/imports/{import_id}/issues")

    assert sheets.status_code == 200
    assert sheets.json()["sheets"]
    assert rows.status_code == 200
    assert "rows" in rows.json()
    assert issues.status_code == 200
    assert issues.json()["total"] <= rows.json()["total"]
