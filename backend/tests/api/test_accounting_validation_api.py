from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import CanonicalRole, ImportStatus, RowClassification, RowStatus
from app.models import Account, FinancialImport, ImportRow
from tests.conftest import client, seed_test_db, test_engine


def setup_function():
    seed_test_db()


def seed_validation_import(
    session: Session,
    *,
    import_id: int,
    values: dict[CanonicalRole, str],
) -> None:
    job = FinancialImport(
        id=import_id,
        company_id=1,
        period_id=1,
        file_name=f"{import_id}.xlsx",
        status=ImportStatus.READY_FOR_REVIEW,
        period_validated=True,
        approved_sheets=["Balance"],
    )
    session.add(job)
    for offset, (role, value) in enumerate(values.items(), start=1):
        account = Account(
            id=import_id * 10 + offset,
            company_id=1,
            code=f"{import_id}-{offset}",
            name=role.value,
            canonical_role=role,
        )
        session.add(account)
        session.flush()
        session.add(
            ImportRow(
                source_import_id=import_id,
                source_sheet="Balance",
                source_row=offset,
                matched_account_id=account.id,
                ending_balance=Decimal(value),
                status=RowStatus.MATCHED,
                row_classification=RowClassification.CUENTA,
            )
        )
    session.commit()


def test_endpoint_returns_missing_roles():
    with Session(test_engine) as session:
        seed_validation_import(
            session,
            import_id=90,
            values={CanonicalRole.ACTIVO: "100", CanonicalRole.PASIVO: "40"},
        )

    response = client.get("/api/imports/90/accounting-validation")

    assert response.status_code == 200
    assert response.json()["rules"][0]["missing_roles"] == ["PATRIMONIO"]


def test_approve_returns_structured_validation_failure():
    with Session(test_engine) as session:
        seed_validation_import(
            session,
            import_id=91,
            values={
                CanonicalRole.ACTIVO: "100",
                CanonicalRole.PASIVO: "40",
                CanonicalRole.PATRIMONIO: "50",
            },
        )

    response = client.post("/api/imports/91/approve")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ACCOUNTING_VALIDATION_FAILED"


def test_approve_accepts_valid_income_statement_with_zero_tax():
    with Session(test_engine) as session:
        seed_validation_import(
            session,
            import_id=92,
            values={
                CanonicalRole.VENTAS: "150",
                CanonicalRole.COSTO_VENTAS: "50",
                CanonicalRole.UTILIDAD_BRUTA: "100",
                CanonicalRole.GASTOS: "80",
                CanonicalRole.IMPUESTOS: "0",
                CanonicalRole.RESULTADO_EJERCICIO: "20",
            },
        )

    response = client.post("/api/imports/92/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
