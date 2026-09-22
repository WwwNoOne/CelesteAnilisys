from pathlib import Path

from tests.conftest import client, seed_test_db

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
    assert len(data["columns"]) > 0
    assert "rows" in data
    assert len(data["rows"]) <= 50
    assert data["total_rows"] >= len(data["rows"])
    assert "truncated" in data
    assert "row_details" in data
    assert len(data["row_details"]) == len(data["rows"])

    # First row is source_row 1
    assert data["row_details"][0]["source_row"] == 1
    # Check that an extracted account row has status
    matched_detail = next((r for r in data["row_details"] if r["account_name"]), None)
    assert matched_detail is not None
    assert matched_detail["status"] is not None


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
