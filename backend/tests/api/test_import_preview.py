from pathlib import Path

from sqlalchemy.orm import Session

from app.models import ImportRow
from tests.conftest import client, seed_test_db, test_engine

EXAMPLE_FILE = Path("data/examples/2025-BG BENGALA.xlsx")


def setup_function():
    seed_test_db()


def test_preview_returns_rich_metadata_and_preserves_rows():
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

    analyze_res = client.post(f"/api/imports/{import_id}/analyze")
    assert analyze_res.status_code == 200

    preview_res = client.get(f"/api/imports/{import_id}/sheets/2025/preview?limit=50")
    assert preview_res.status_code == 200
    data = preview_res.json()

    assert data["sheet_name"] == "2025"
    assert "columns" in data
    assert data["columns"] == ["Cuenta", "Saldo"]
    assert "rows" in data
    assert len(data["rows"]) <= 50
    assert data["total_rows"] >= len(data["rows"])
    assert "truncated" in data
    assert "row_details" in data
    assert len(data["row_details"]) == len(data["rows"])

    # Each normalized row represents one extracted account line.
    matched_detail = next((r for r in data["row_details"] if r["account_name"]), None)
    assert matched_detail is not None
    assert matched_detail["status"] is not None
    assert matched_detail["source_row"] >= 1


def test_preview_returns_422_for_invalid_sheet():
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
    import_id = response.json()["id"]
    client.post(f"/api/imports/{import_id}/analyze")

    res = client.get(f"/api/imports/{import_id}/sheets/NON_EXISTENT/preview")
    assert res.status_code == 422


def test_preview_renders_each_lateral_candidate_as_separate_line():
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
    import_id = response.json()["id"]
    client.post(f"/api/imports/{import_id}/analyze")

    with Session(test_engine) as session:
        imported_rows = (
            session.query(ImportRow)
            .filter(
                ImportRow.source_import_id == import_id,
                ImportRow.source_sheet == "2025",
            )
            .all()
        )
    counts: dict[int, int] = {}
    for row in imported_rows:
        counts[row.source_row] = counts.get(row.source_row, 0) + 1
    duplicated_source_row = next(row for row, count in counts.items() if count > 1)

    # The extraction keeps both lateral candidates in import_rows...
    assert counts[duplicated_source_row] > 1

    # ...and the normalized preview renders each one as its own line.
    preview = client.get(f"/api/imports/{import_id}/sheets/2025/preview?limit=200").json()
    visible = [
        detail
        for detail in preview["row_details"]
        if detail["source_row"] == duplicated_source_row
    ]

    assert len(visible) == counts[duplicated_source_row]
    assert len({detail["import_row_id"] for detail in visible}) == counts[duplicated_source_row]
