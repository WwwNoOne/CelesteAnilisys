from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.domain.enums import ImportStatus, MatchType, RowStatus
from app.importers.excel_reader import read_workbook
from app.importers.header_detector import detect_header
from app.importers.sheet_classifier import classify_sheet
from app.models import Company, FinancialImport, ImportRow, Period
from app.services.account_extraction_service import extract_account_candidates
from app.services.account_matching_service import AccountCatalog, match_account

IMPORT_STORAGE_DIR = Path("data/imports")


def create_import(
    db: Session,
    file: UploadFile,
    company_id: int,
    period_id: int,
) -> FinancialImport:
    _require_references(db, company_id, period_id)
    _validate_extension(file.filename or "")

    import_job = FinancialImport(
        company_id=company_id,
        period_id=period_id,
        file_name=file.filename or "archivo.xlsx",
    )
    db.add(import_job)
    db.flush()

    IMPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{import_job.id}-{uuid4().hex}{Path(import_job.file_name).suffix.lower()}"
    storage_path = IMPORT_STORAGE_DIR / safe_name
    storage_path.write_bytes(file.file.read())
    import_job.storage_path = str(storage_path)
    db.commit()
    db.refresh(import_job)
    return import_job


def analyze_import(db: Session, import_job: FinancialImport) -> FinancialImport:
    if not import_job.storage_path:
        raise ValueError("La importación no tiene archivo almacenado")

    import_job.status = ImportStatus.ANALYZING
    db.commit()
    try:
        workbook = read_workbook(Path(import_job.storage_path))
        catalog = _catalog_for_company(db, import_job.company_id)
        for sheet in workbook.sheets:
            header = detect_header(sheet.rows)
            if header.row_index is None:
                continue
            for candidate in extract_account_candidates(sheet, header):
                result = match_account(
                    {
                        "code": candidate.code,
                        "name": candidate.name,
                        "normalized_name": candidate.normalized_name,
                        "context_codes": candidate.context_codes,
                    },
                    catalog,
                )
                db.add(
                    ImportRow(
                        source_import_id=import_job.id,
                        source_sheet=candidate.sheet,
                        source_row=candidate.excel_row,
                        original_code=candidate.code,
                        original_name=candidate.name,
                        normalized_name=candidate.normalized_name,
                        matched_account_id=result.account.id if result.account else None,
                        match_type=result.match_type,
                        confidence=result.confidence,
                        status=result.status,
                    )
                )

        db.flush()
        _refresh_summary(import_job, db)
        import_job.status = ImportStatus.READY_FOR_REVIEW
        db.commit()
    except Exception:
        db.rollback()
        import_job = db.get(FinancialImport, import_job.id)
        if import_job is not None:
            import_job.status = ImportStatus.FAILED
            db.commit()
        raise

    db.refresh(import_job)
    return import_job


def get_sheet_analysis(import_job: FinancialImport) -> list[dict]:
    workbook = read_workbook(Path(import_job.storage_path or ""))
    results = []
    for sheet in workbook.sheets:
        classification = classify_sheet(sheet.name, sheet.rows)
        header = detect_header(sheet.rows)
        results.append(
            {
                "sheet_name": classification.sheet_name,
                "normalized_name": classification.normalized_name,
                "sheet_type": classification.sheet_type.value,
                "confidence": classification.confidence,
                "header_row": header.row_index,
                "header_columns": header.columns,
            }
        )
    return results


def get_sheet_preview(import_job: FinancialImport, sheet_name: str, limit: int = 80) -> list[list]:
    workbook = read_workbook(Path(import_job.storage_path or ""))
    sheet = next((item for item in workbook.sheets if item.name == sheet_name), None)
    if sheet is None:
        raise ValueError("Hoja no encontrada")
    return [
        [value.isoformat() if hasattr(value, "isoformat") else value for value in row[:20]]
        for row in sheet.rows[:limit]
    ]


def review_row(db: Session, import_job: FinancialImport, row_id: int, action: str, account_id: int | None) -> FinancialImport:
    from app.models import Account

    row = db.query(ImportRow).filter(ImportRow.id == row_id, ImportRow.source_import_id == import_job.id).first()
    if row is None:
        raise ValueError("Fila de importación no encontrada")
    if action == "ignore":
        row.status = RowStatus.IGNORED
        row.match_type = MatchType.NONE
        row.matched_account_id = None
    elif action == "match" and account_id is not None:
        account = db.query(Account).filter(Account.id == account_id, Account.company_id == import_job.company_id).first()
        if account is None:
            raise ValueError("La cuenta indicada no pertenece a la empresa")
        row.matched_account_id = account.id
        row.match_type = MatchType.CODE_AND_NAME
        row.confidence = 1
        row.status = RowStatus.MATCHED
    else:
        raise ValueError("Acción de revisión no soportada")
    _refresh_summary(import_job, db)
    db.commit()
    db.refresh(import_job)
    return import_job


def approve_import(db: Session, import_job: FinancialImport) -> FinancialImport:
    pending = db.query(ImportRow).filter(
        ImportRow.source_import_id == import_job.id,
        ImportRow.status.in_([RowStatus.NEEDS_REVIEW, RowStatus.UNKNOWN, RowStatus.NEW_ACCOUNT, RowStatus.ERROR]),
    ).count()
    if pending:
        raise ValueError("La importación todavía tiene filas pendientes de revisión")
    import_job.status = ImportStatus.APPROVED
    db.commit()
    db.refresh(import_job)
    return import_job


def _refresh_summary(import_job: FinancialImport, db: Session) -> None:
    rows = db.query(ImportRow).filter(ImportRow.source_import_id == import_job.id).all()
    import_job.total_rows = len(rows)
    import_job.recognized_rows = sum(row.status is RowStatus.MATCHED for row in rows)
    import_job.review_rows = sum(row.status in {
        RowStatus.NEEDS_REVIEW,
        RowStatus.UNKNOWN,
        RowStatus.NEW_ACCOUNT,
        RowStatus.ERROR,
    } for row in rows)
    import_job.new_accounts = sum(row.status is RowStatus.NEW_ACCOUNT for row in rows)
    import_job.error_rows = sum(row.status is RowStatus.ERROR for row in rows)


def _catalog_for_company(db: Session, company_id: int) -> AccountCatalog:
    from app.models import Account, AccountAlias

    accounts = db.query(Account).filter(Account.company_id == company_id).all()
    aliases = (
        db.query(AccountAlias)
        .join(Account)
        .filter(Account.company_id == company_id)
        .all()
    )
    return AccountCatalog(accounts=accounts, aliases=aliases)


def _require_references(db: Session, company_id: int, period_id: int) -> None:
    if db.get(Company, company_id) is None:
        raise ValueError("La empresa indicada no existe")
    if db.get(Period, period_id) is None:
        raise ValueError("El período indicado no existe")


def _validate_extension(file_name: str) -> None:
    if Path(file_name).suffix.lower() not in {".xlsx", ".xlsm"}:
        raise ValueError("Formato no soportado. Use .xlsx o .xlsm")
