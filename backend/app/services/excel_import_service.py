from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.domain.enums import CanonicalRole, ImportStatus, MatchType, RowClassification, RowStatus
from app.importers.excel_reader import read_workbook
from app.importers.header_detector import detect_header
from app.importers.sheet_classifier import classify_sheet
from app.models import AccountBalance, Company, FinancialImport, ImportRow, Period
from app.schemas.import_api import (
    PreviewResponse,
    SheetApprovalRequest,
    SheetApprovalResponse,
    SheetPreviewRow,
)
from app.services.account_extraction_service import extract_account_candidates
from app.services.account_matching_service import AccountCatalog, match_account
from app.services.accounting_validation_service import validate_import_accounting
from app.services.period_detection_service import (
    detect_period,
    detect_sheet_temporal_info,
)
from app.services.statement_duplicate_service import check_statement_duplicate

IMPORT_STORAGE_DIR = Path("data/imports")


class AccountingValidationError(ValueError):
    def __init__(self, validation):
        super().__init__("La validación contable tiene errores bloqueantes")
        self.validation = validation


def delete_pending_import(db: Session, import_job: FinancialImport) -> None:
    if import_job.status != ImportStatus.READY_FOR_REVIEW:
        raise ValueError("Solo se pueden eliminar importaciones pendientes de revisión")

    storage_path = Path(import_job.storage_path) if import_job.storage_path else None
    db.query(AccountBalance).filter(
        AccountBalance.source_import_id == import_job.id
    ).delete(synchronize_session=False)
    db.query(ImportRow).filter(
        ImportRow.source_import_id == import_job.id
    ).delete(synchronize_session=False)
    db.delete(import_job)
    db.commit()

    if storage_path is not None:
        storage_path.unlink(missing_ok=True)


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
        detection = detect_period(import_job.file_name, workbook.sheets)
        import_job.detected_period_label = detection.label
        import_job.detected_period_year = detection.year
        import_job.detected_period_month = detection.month
        import_job.period_source = detection.source
        import_job.period_conflict = detection.conflict
        import_job.detected_statement_type = detection.statement_type
        import_job.detected_as_of_date = detection.as_of_date
        import_job.detected_period_start = detection.period_start
        import_job.detected_period_end = detection.period_end
        import_job.detected_timeframe = detection.timeframe
        import_job.period_validated = False
        catalog = _catalog_for_company(db, import_job.company_id)
        for sheet in workbook.sheets:
            header = detect_header(sheet.rows)
            if header.row_index is None:
                continue
            for candidate in extract_account_candidates(sheet, header):
                if candidate.row_classification in (
                    RowClassification.ENCABEZADO,
                    RowClassification.NOTA,
                    RowClassification.IGNORAR,
                ):
                    matched_account_id = None
                    match_type = MatchType.NONE
                    confidence = 1.0
                    status = RowStatus.MATCHED
                else:
                    result = match_account(
                        {
                            "code": candidate.code,
                            "name": candidate.name,
                            "normalized_name": candidate.normalized_name,
                            "context_codes": candidate.context_codes,
                        },
                        catalog,
                    )
                    matched_account_id = result.account.id if result.account else None
                    match_type = result.match_type
                    confidence = result.confidence
                    status = result.status

                db.add(
                    ImportRow(
                        source_import_id=import_job.id,
                        source_sheet=candidate.sheet,
                        source_row=candidate.excel_row,
                        original_code=candidate.code,
                        original_name=candidate.name,
                        normalized_name=candidate.normalized_name,
                        matched_account_id=matched_account_id,
                        match_type=match_type,
                        confidence=confidence,
                        status=status,
                        row_classification=candidate.row_classification,
                        opening_balance=candidate.opening_balance,
                        debits=candidate.debits,
                        credits=candidate.credits,
                        ending_balance=candidate.ending_balance,
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
        temporal_info = detect_sheet_temporal_info(sheet)
        results.append(
            {
                "sheet_name": classification.sheet_name,
                "normalized_name": classification.normalized_name,
                "sheet_type": classification.sheet_type.value,
                "confidence": classification.confidence,
                "header_row": header.row_index,
                "header_columns": header.columns,
                "as_of_date": temporal_info.get("as_of_date"),
                "period_start": temporal_info.get("period_start"),
                "period_end": temporal_info.get("period_end"),
                "timeframe": temporal_info.get("timeframe"),
                "date_label": temporal_info.get("date_label"),
            }
        )
    return results


def get_sheet_preview(
    import_job: FinancialImport,
    sheet_name: str,
    db: Session | None = None,
    limit: int = 200,
) -> PreviewResponse:
    workbook = read_workbook(Path(import_job.storage_path or ""))
    sheet = next((item for item in workbook.sheets if item.name == sheet_name), None)
    if sheet is None:
        raise ValueError("Hoja no encontrada")

    temporal_info = detect_sheet_temporal_info(sheet)
    import_rows_by_line: dict[int, list[ImportRow]] = {}
    if db is not None and import_job.id:
        rows = (
            db.query(ImportRow)
            .filter(
                ImportRow.source_import_id == import_job.id,
                ImportRow.source_sheet == sheet_name,
            )
            .order_by(ImportRow.source_row, ImportRow.id)
            .all()
        )
        for r in rows:
            import_rows_by_line.setdefault(r.source_row, []).append(r)

    max_cols = max((len(r) for r in sheet.rows[:limit]), default=0)
    col_count = min(max(max_cols, 1), 26)
    columns = [chr(65 + i) for i in range(col_count)]

    raw_rows = []
    row_details = []
    for line_num, r in enumerate(sheet.rows[:limit], start=1):
        formatted_row = [value.isoformat() if hasattr(value, "isoformat") else value for value in r[:col_count]]
        matched_rows = import_rows_by_line.get(line_num) or [None]
        for matched_row in matched_rows:
            raw_rows.append(formatted_row)
            row_details.append(
                SheetPreviewRow(
                    source_row=line_num,
                    cells=formatted_row,
                    import_row_id=matched_row.id if matched_row else None,
                    status=matched_row.status.value if matched_row else None,
                    account_code=matched_row.original_code if matched_row else None,
                    account_name=matched_row.original_name if matched_row else None,
                    row_classification=(
                        matched_row.row_classification.value if matched_row else "CUENTA"
                    ),
                    canonical_role=(
                        matched_row.matched_account.canonical_role
                        if matched_row and matched_row.matched_account
                        else None
                    ),
                    ending_balance=matched_row.ending_balance if matched_row else None,
                )
            )

    expanded_preview_truncated = len(raw_rows) > limit
    raw_rows = raw_rows[:limit]
    row_details = row_details[:limit]

    return PreviewResponse(
        sheet_name=sheet_name,
        columns=columns,
        rows=raw_rows,
        total_rows=len(sheet.rows),
        truncated=len(sheet.rows) > limit or expanded_preview_truncated,
        row_details=row_details,
        as_of_date=temporal_info.get("as_of_date"),
        period_start=temporal_info.get("period_start"),
        period_end=temporal_info.get("period_end"),
        timeframe=temporal_info.get("timeframe"),
        date_label=temporal_info.get("date_label"),
    )


def review_row(
    db: Session,
    import_job: FinancialImport,
    row_id: int,
    action: str,
    account_id: int | None = None,
    row_classification: RowClassification | None = None,
    canonical_role: CanonicalRole | None = None,
    ending_balance: Decimal | None = None,
) -> FinancialImport:
    from app.models import Account

    row = db.query(ImportRow).filter(ImportRow.id == row_id, ImportRow.source_import_id == import_job.id).first()
    if row is None:
        raise ValueError("Fila de importación no encontrada")

    if action == "classify" and row_classification is not None:
        try:
            rc = RowClassification(row_classification)
        except ValueError:
            raise ValueError(f"Clasificación no válida: {row_classification}")
        row.row_classification = rc
        if rc == RowClassification.IGNORAR:
            row.status = RowStatus.IGNORED
            row.match_type = MatchType.NONE
            row.matched_account_id = None
        elif rc in (
            RowClassification.SUBTOTAL,
            RowClassification.TOTAL,
            RowClassification.ENCABEZADO,
            RowClassification.NOTA,
        ):
            row.status = RowStatus.MATCHED
            row.match_type = MatchType.NONE
            row.matched_account_id = None
        elif rc == RowClassification.CUENTA:
            if row.matched_account_id:
                row.status = RowStatus.MATCHED
            else:
                row.status = RowStatus.UNKNOWN
    elif action == "ignore":
        row.row_classification = RowClassification.IGNORAR
        row.status = RowStatus.IGNORED
        row.match_type = MatchType.NONE
        row.matched_account_id = None
    elif action == "update_financial_line":
        if (
            account_id is None
            or row_classification is None
            or canonical_role is None
            or ending_balance is None
        ):
            raise ValueError("Cuenta, clasificación, rol y saldo son obligatorios")
        account = (
            db.query(Account)
            .filter(
                Account.id == account_id,
                Account.company_id == import_job.company_id,
            )
            .first()
        )
        if account is None:
            raise ValueError("La cuenta indicada no pertenece a la empresa")
        account.canonical_role = canonical_role
        row.row_classification = row_classification
        row.ending_balance = ending_balance
        row.matched_account_id = account.id
        row.match_type = MatchType.CODE_AND_NAME
        row.confidence = 1
        row.status = RowStatus.MATCHED
    elif action == "match" and account_id is not None:
        account = db.query(Account).filter(Account.id == account_id, Account.company_id == import_job.company_id).first()
        if account is None:
            raise ValueError("La cuenta indicada no pertenece a la empresa")
        row.row_classification = RowClassification.CUENTA
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


def approve_sheet(
    db: Session,
    import_job: FinancialImport,
    sheet_name: str,
    payload: SheetApprovalRequest,
) -> SheetApprovalResponse:
    sheet_rows = (
        db.query(ImportRow)
        .filter(
            ImportRow.source_import_id == import_job.id,
            ImportRow.source_sheet == sheet_name,
        )
        .all()
    )
    if not sheet_rows:
        raise ValueError(f"No hay filas registradas para la hoja '{sheet_name}'")

    blocking = [
        r
        for r in sheet_rows
        if r.row_classification == RowClassification.CUENTA
        and r.status
        in (
            RowStatus.NEEDS_REVIEW,
            RowStatus.UNKNOWN,
            RowStatus.NEW_ACCOUNT,
            RowStatus.ERROR,
        )
    ]
    if blocking:
        raise ValueError(
            f"La hoja '{sheet_name}' tiene {len(blocking)} fila(s) contable(s) pendiente(s) de revisión"
        )

    temporal: dict = {}
    if import_job.storage_path and Path(import_job.storage_path).exists():
        try:
            workbook = read_workbook(Path(import_job.storage_path))
            sheet = next((s for s in workbook.sheets if s.name == sheet_name), None)
            if sheet:
                temporal = detect_sheet_temporal_info(sheet)
        except (FileNotFoundError, ValueError, OSError):
            temporal = {}

    statement_type = (
        payload.statement_type or temporal.get("statement_type") or "ESTADO_RESULTADOS"
    )
    as_of_date = payload.as_of_date or temporal.get("as_of_date")
    period_start = payload.period_start or temporal.get("period_start")
    period_end = payload.period_end or temporal.get("period_end")
    timeframe = payload.timeframe or temporal.get("timeframe") or "ANNUAL"
    year = (
        payload.year
        or temporal.get("year")
        or (as_of_date.year if as_of_date else import_job.detected_period_year or 2025)
    )
    label = payload.label or temporal.get("date_label") or str(year)

    dup_result = check_statement_duplicate(
        db,
        company_id=import_job.company_id,
        statement_type=statement_type,
        as_of_date=as_of_date,
        period_start=period_start,
        period_end=period_end,
        exclude_import_id=import_job.id,
    )
    if dup_result.is_duplicate and not payload.overwrite:
        return SheetApprovalResponse(
            success=False,
            sheet_name=sheet_name,
            status="DUPLICATE_WARNING",
            balances_saved=0,
            is_duplicate=True,
            duplicate_warning=dup_result.duplicate_reason,
            period_id=dup_result.existing_period_id,
        )

    period = _find_or_create_period(
        db=db,
        year=year,
        label=label,
        statement_type=statement_type,
        as_of_date=as_of_date,
        period_start=period_start,
        period_end=period_end,
        timeframe=timeframe,
    )

    valid_rows = [
        r
        for r in sheet_rows
        if r.row_classification
        in (
            RowClassification.CUENTA,
            RowClassification.SUBTOTAL,
            RowClassification.TOTAL,
        )
        and r.matched_account_id is not None
    ]
    saved_count = _persist_balances(
        db=db,
        company_id=import_job.company_id,
        period_id=period.id,
        source_import_id=import_job.id,
        source_sheet=sheet_name,
        rows=valid_rows,
        overwrite=payload.overwrite,
    )

    approved_sheets = list(import_job.approved_sheets or [])
    if sheet_name not in approved_sheets:
        approved_sheets.append(sheet_name)
    import_job.approved_sheets = approved_sheets

    db.commit()
    db.refresh(import_job)

    return SheetApprovalResponse(
        success=True,
        sheet_name=sheet_name,
        status="APPROVED",
        balances_saved=saved_count,
        period_id=period.id,
    )


def approve_import(db: Session, import_job: FinancialImport) -> FinancialImport:
    if not import_job.period_validated or import_job.period_conflict:
        raise ValueError("El período debe validarse antes de aprobar la importación")
    pending = db.query(ImportRow).filter(
        ImportRow.source_import_id == import_job.id,
        ImportRow.row_classification == RowClassification.CUENTA,
        ImportRow.status.in_([
            RowStatus.NEEDS_REVIEW,
            RowStatus.UNKNOWN,
            RowStatus.NEW_ACCOUNT,
            RowStatus.ERROR,
        ]),
    ).count()
    if pending:
        raise ValueError("La importación todavía tiene filas pendientes de revisión")

    required_sheets = {
        source_sheet
        for (source_sheet,) in db.query(ImportRow.source_sheet)
        .filter(
            ImportRow.source_import_id == import_job.id,
            ImportRow.row_classification == RowClassification.CUENTA,
        )
        .distinct()
        .all()
    }
    missing_sheets = required_sheets - set(import_job.approved_sheets or [])
    if missing_sheets:
        names = ", ".join(sorted(missing_sheets))
        raise ValueError(f"Faltan hojas por guardar antes de aprobar: {names}")

    validation = validate_import_accounting(db, import_job.id)
    if not validation.valid:
        raise AccountingValidationError(validation)

    import_job.status = ImportStatus.APPROVED
    db.commit()
    db.refresh(import_job)
    return import_job


def _find_or_create_period(
    db: Session,
    year: int,
    label: str,
    statement_type: str,
    as_of_date: date | None,
    period_start: date | None,
    period_end: date | None,
    timeframe: str,
) -> Period:
    query = db.query(Period).filter(Period.year == year)
    if as_of_date:
        query = query.filter(Period.as_of_date == as_of_date)
    if period_start:
        query = query.filter(Period.period_start == period_start)
    if period_end:
        query = query.filter(Period.period_end == period_end)
    period = query.first()
    if period is None:
        period = Period(
            year=year,
            label=label,
            statement_type=statement_type,
            as_of_date=as_of_date,
            period_start=period_start,
            period_end=period_end,
            timeframe=timeframe,
        )
        db.add(period)
        db.flush()
    return period


def _persist_balances(
    db: Session,
    company_id: int,
    period_id: int,
    source_import_id: int,
    source_sheet: str,
    rows: list[ImportRow],
    overwrite: bool = False,
) -> int:
    saved = 0
    rows_by_account: dict[int, list[ImportRow]] = {}
    for row in rows:
        if row.matched_account_id is not None:
            rows_by_account.setdefault(row.matched_account_id, []).append(row)

    selected_rows: list[ImportRow] = []
    for account_rows in rows_by_account.values():
        ordered = sorted(account_rows, key=lambda row: (row.source_row, row.id))
        declared_values = {row.ending_balance for row in ordered}
        if len(declared_values) > 1:
            raise ValueError("Una cuenta tiene saldos distintos en el mismo período")
        selected_rows.append(ordered[0])

    for r in selected_rows:
        if r.matched_account_id is None:
            continue
        is_authoritative = bool(
            r.matched_account
            and r.matched_account.canonical_role is not None
            and r.row_classification
            in (RowClassification.CUENTA, RowClassification.SUBTOTAL, RowClassification.TOTAL)
        )
        existing = db.query(AccountBalance).filter(
            AccountBalance.company_id == company_id,
            AccountBalance.period_id == period_id,
            AccountBalance.account_id == r.matched_account_id,
        ).first()

        if existing:
            if overwrite or existing.source_import_id == source_import_id:
                existing.opening_balance = r.opening_balance
                existing.debits = r.debits
                existing.credits = r.credits
                existing.ending_balance = r.ending_balance
                existing.source_import_id = source_import_id
                existing.source_sheet = source_sheet
                existing.source_row = r.source_row
                existing.is_authoritative = is_authoritative
                saved += 1
        else:
            balance = AccountBalance(
                company_id=company_id,
                period_id=period_id,
                account_id=r.matched_account_id,
                source_import_id=source_import_id,
                opening_balance=r.opening_balance,
                debits=r.debits,
                credits=r.credits,
                ending_balance=r.ending_balance,
                is_authoritative=is_authoritative,
                source_sheet=source_sheet,
                source_row=r.source_row,
            )
            db.add(balance)
            saved += 1
    db.flush()
    return saved


def _refresh_summary(import_job: FinancialImport, db: Session) -> None:
    rows = db.query(ImportRow).filter(ImportRow.source_import_id == import_job.id).all()
    import_job.total_rows = len(rows)
    import_job.recognized_rows = sum(row.status == RowStatus.MATCHED for row in rows)
    import_job.review_rows = sum(row.status in {
        RowStatus.NEEDS_REVIEW,
        RowStatus.UNKNOWN,
        RowStatus.NEW_ACCOUNT,
        RowStatus.ERROR,
    } for row in rows)
    import_job.unknown_rows = sum(row.status == RowStatus.UNKNOWN for row in rows)
    import_job.new_accounts = sum(row.status == RowStatus.NEW_ACCOUNT for row in rows)
    import_job.error_rows = sum(row.status == RowStatus.ERROR for row in rows)


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
