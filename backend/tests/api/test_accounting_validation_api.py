from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus, RowClassification, RowStatus
from app.models import FinancialImport, ImportRow
from tests.conftest import client, seed_test_db, test_engine


def setup_function():
    seed_test_db()


def seed_sheet(
    session: Session,
    *,
    import_id: int,
    lines: list[tuple[str, RowClassification, str | None]],
    sheet: str = "BG",
    approved: bool = True,
) -> None:
    job = FinancialImport(
        id=import_id,
        company_id=1,
        period_id=1,
        file_name=f"{import_id}.xlsx",
        status=ImportStatus.READY_FOR_REVIEW,
        period_validated=True,
        approved_sheets=[sheet] if approved else [],
    )
    session.add(job)
    for source_row, (name, classification, balance) in enumerate(lines, start=6):
        session.add(
            ImportRow(
                source_import_id=import_id,
                source_sheet=sheet,
                source_row=source_row,
                source_text_column=0,
                original_name=name,
                normalized_name=name.upper(),
                status=RowStatus.MATCHED,
                row_classification=classification,
                ending_balance=Decimal(balance) if balance is not None else None,
            )
        )
    session.commit()


def test_endpoint_returns_mismatch_for_unbalanced_total():
    with Session(test_engine) as session:
        seed_sheet(
            session,
            import_id=90,
            lines=[
                ("ACTIVOS", RowClassification.ENCABEZADO, None),
                ("CORRIENTE", RowClassification.SUBTOTAL, "40"),
                ("NO CORRIENTE", RowClassification.SUBTOTAL, "50"),
                ("TOTAL ACTIVO", RowClassification.TOTAL, "100"),
            ],
        )

    response = client.get("/api/imports/90/accounting-validation")

    assert response.status_code == 200
    total_rule = next(r for r in response.json()["rules"] if r["rule_id"].startswith("total_"))
    assert total_rule["status"] == "MISMATCH"
    assert Decimal(total_rule["left_value"]) == Decimal(100)
    assert Decimal(total_rule["right_value"]) == Decimal(90)


def test_approve_returns_structured_validation_failure():
    with Session(test_engine) as session:
        seed_sheet(
            session,
            import_id=91,
            lines=[
                ("ACTIVOS", RowClassification.ENCABEZADO, None),
                ("CORRIENTE", RowClassification.SUBTOTAL, "40"),
                ("NO CORRIENTE", RowClassification.SUBTOTAL, "50"),
                ("TOTAL ACTIVO", RowClassification.TOTAL, "100"),
            ],
        )

    response = client.post("/api/imports/91/approve")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ACCOUNTING_VALIDATION_FAILED"


def test_approve_accepts_balanced_statement():
    with Session(test_engine) as session:
        seed_sheet(
            session,
            import_id=92,
            lines=[
                ("ACTIVOS", RowClassification.ENCABEZADO, None),
                ("CORRIENTE", RowClassification.SUBTOTAL, "60"),
                ("NO CORRIENTE", RowClassification.SUBTOTAL, "40"),
                ("TOTAL ACTIVO", RowClassification.TOTAL, "100"),
                ("PASIVOS", RowClassification.ENCABEZADO, None),
                ("PASIVO CORRIENTE", RowClassification.SUBTOTAL, "100"),
                ("TOTAL PASIVO y PATRIMONIO", RowClassification.TOTAL, "100"),
            ],
        )

    response = client.post("/api/imports/92/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
