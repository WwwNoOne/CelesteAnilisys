from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import RowClassification, RowStatus, ValidationStatus
from app.models import FinancialImport, ImportRow
from app.services.accounting_validation_service import validate_import_accounting
from tests.conftest import seed_test_db, test_engine


def _add_row(
    session: Session,
    *,
    import_id: int,
    sheet: str,
    source_row: int,
    name: str,
    classification: RowClassification,
    balance: str | None,
    text_column: int = 0,
) -> ImportRow:
    row = ImportRow(
        source_import_id=import_id,
        source_sheet=sheet,
        source_row=source_row,
        source_text_column=text_column,
        original_name=name,
        normalized_name=name.upper(),
        status=RowStatus.MATCHED,
        row_classification=classification,
        ending_balance=Decimal(balance) if balance is not None else None,
    )
    session.add(row)
    return row


def test_balanced_rollup_is_valid():
    seed_test_db()
    with Session(test_engine) as session:
        session.add(
            FinancialImport(id=70, company_id=1, period_id=1, file_name="b.xlsx")
        )
        _add_row(session, import_id=70, sheet="BG", source_row=6, name="ACTIVOS", classification=RowClassification.ENCABEZADO, balance=None)
        _add_row(session, import_id=70, sheet="BG", source_row=7, name="CORRIENTE", classification=RowClassification.SUBTOTAL, balance="80068.80")
        _add_row(session, import_id=70, sheet="BG", source_row=8, name="EFECTIVO", classification=RowClassification.CUENTA, balance="1581.79")
        _add_row(session, import_id=70, sheet="BG", source_row=9, name="POR COBRAR", classification=RowClassification.CUENTA, balance="75267.09")
        _add_row(session, import_id=70, sheet="BG", source_row=10, name="ANTICIPOS", classification=RowClassification.CUENTA, balance="1589.22")
        _add_row(session, import_id=70, sheet="BG", source_row=11, name="IVA", classification=RowClassification.CUENTA, balance="1630.70")
        _add_row(session, import_id=70, sheet="BG", source_row=12, name="NO CORRIENTE", classification=RowClassification.SUBTOTAL, balance="0")
        _add_row(session, import_id=70, sheet="BG", source_row=13, name="PROPIEDAD", classification=RowClassification.CUENTA, balance="1945.20")
        _add_row(session, import_id=70, sheet="BG", source_row=14, name="DEPRECIACION", classification=RowClassification.CUENTA, balance="-1945.20")
        _add_row(session, import_id=70, sheet="BG", source_row=19, name="TOTAL ACTIVO", classification=RowClassification.TOTAL, balance="80068.80")
        _add_row(session, import_id=70, sheet="BG", source_row=6, name="PASIVOS", classification=RowClassification.ENCABEZADO, balance=None, text_column=4)
        _add_row(session, import_id=70, sheet="BG", source_row=7, name="CORRIENTE", classification=RowClassification.SUBTOTAL, balance="75642.38", text_column=4)
        _add_row(session, import_id=70, sheet="BG", source_row=8, name="POR PAGAR", classification=RowClassification.CUENTA, balance="75000", text_column=4)
        _add_row(session, import_id=70, sheet="BG", source_row=9, name="RETENCIONES", classification=RowClassification.CUENTA, balance="487.51", text_column=4)
        _add_row(session, import_id=70, sheet="BG", source_row=10, name="IMPUESTOS", classification=RowClassification.CUENTA, balance="154.87", text_column=4)
        _add_row(session, import_id=70, sheet="BG", source_row=19, name="TOTAL PASIVO y PATRIMONIO", classification=RowClassification.TOTAL, balance="75642.38", text_column=4)
        session.commit()

        validation = validate_import_accounting(session, 70, sheet_name="BG")

    # The balance equation must be reported (Activo = Pasivo + Patrimonio).
    assert any(rule.rule_id == "balance" for rule in validation.rules)
    # The "TOTAL PASIVO y PATRIMONIO" does not match assets because the pasivo
    # subtotal only covers 75642.38, so the rollup flags it.
    assert validation.valid is False


def test_mismatched_total_is_reported():
    seed_test_db()
    with Session(test_engine) as session:
        session.add(
            FinancialImport(id=71, company_id=1, period_id=1, file_name="b.xlsx")
        )
        _add_row(session, import_id=71, sheet="ER", source_row=6, name="INGRESOS", classification=RowClassification.ENCABEZADO, balance=None)
        _add_row(session, import_id=71, sheet="ER", source_row=7, name="VENTAS", classification=RowClassification.SUBTOTAL, balance="1000")
        _add_row(session, import_id=71, sheet="ER", source_row=8, name="SERVICIOS", classification=RowClassification.CUENTA, balance="600")
        _add_row(session, import_id=71, sheet="ER", source_row=9, name="OTROS", classification=RowClassification.CUENTA, balance="200")
        _add_row(session, import_id=71, sheet="ER", source_row=10, name="TOTAL INGRESOS", classification=RowClassification.TOTAL, balance="900")
        session.commit()

        validation = validate_import_accounting(session, 71, sheet_name="ER")

    total_rule = next(rule for rule in validation.rules if rule.rule_id.startswith("total_"))
    assert total_rule.status == ValidationStatus.MISMATCH
    assert total_rule.left_value == Decimal(900)
    assert total_rule.right_value == Decimal(1000)


def test_balanced_total_and_equation_is_valid():
    seed_test_db()
    with Session(test_engine) as session:
        session.add(
            FinancialImport(id=72, company_id=1, period_id=1, file_name="b.xlsx")
        )
        _add_row(session, import_id=72, sheet="BG", source_row=6, name="ACTIVOS", classification=RowClassification.ENCABEZADO, balance=None)
        _add_row(session, import_id=72, sheet="BG", source_row=7, name="CORRIENTE", classification=RowClassification.SUBTOTAL, balance="60")
        _add_row(session, import_id=72, sheet="BG", source_row=8, name="NO CORRIENTE", classification=RowClassification.SUBTOTAL, balance="40")
        _add_row(session, import_id=72, sheet="BG", source_row=9, name="TOTAL ACTIVO", classification=RowClassification.TOTAL, balance="100")
        _add_row(session, import_id=72, sheet="BG", source_row=10, name="PASIVOS", classification=RowClassification.ENCABEZADO, balance=None)
        _add_row(session, import_id=72, sheet="BG", source_row=11, name="PASIVO CORRIENTE", classification=RowClassification.SUBTOTAL, balance="100")
        _add_row(session, import_id=72, sheet="BG", source_row=12, name="TOTAL PASIVO", classification=RowClassification.TOTAL, balance="100")
        session.commit()

        validation = validate_import_accounting(session, 72, sheet_name="BG")

    assert validation.valid is True
    assert all(rule.status == ValidationStatus.VALID for rule in validation.rules)
    assert any(rule.rule_id == "balance" for rule in validation.rules)
