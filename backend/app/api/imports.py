from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.enums import RowStatus
from app.models import FinancialImport, ImportRow
from app.schemas.accounting_validation import AccountingValidationResponse
from app.schemas.import_api import (
    ImportResponse,
    ImportRowsResponse,
    PeriodUpdate,
    PreviewResponse,
    RowReviewUpdate,
    SheetApprovalRequest,
    SheetApprovalResponse,
    SheetsResponse,
)
from app.services.accounting_validation_service import validate_import_accounting
from app.services.excel_import_service import (
    AccountingValidationError,
    analyze_import,
    approve_import,
    approve_sheet,
    create_import,
    delete_pending_import,
    get_sheet_analysis,
    get_sheet_preview,
    review_row,
)

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.get("/{import_id}/accounting-validation", response_model=AccountingValidationResponse)
def get_accounting_validation(
    import_id: int,
    sheet_name: str | None = None,
    db: Session = Depends(get_db),
) -> AccountingValidationResponse:
    if db.get(FinancialImport, import_id) is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    return validate_import_accounting(db, import_id, sheet_name=sheet_name)


@router.delete("/{import_id}", status_code=204)
def delete_import(import_id: int, db: Session = Depends(get_db)) -> None:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        delete_pending_import(db, import_job)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("", response_model=ImportResponse, status_code=201)
def upload_import(
    company_id: int = Form(...),
    period_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> FinancialImport:
    try:
        return create_import(db, file, company_id, period_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/{import_id}/analyze", response_model=ImportResponse)
def analyze_uploaded_import(import_id: int, db: Session = Depends(get_db)) -> FinancialImport:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return analyze_import(db, import_job)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{import_id}", response_model=ImportResponse)
def get_import(import_id: int, db: Session = Depends(get_db)) -> FinancialImport:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    return import_job


@router.patch("/{import_id}/period", response_model=ImportResponse)
def update_import_period(import_id: int, payload: PeriodUpdate, db: Session = Depends(get_db)) -> FinancialImport:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    import_job.detected_period_label = payload.label.strip()
    import_job.detected_period_year = payload.year
    import_job.detected_period_month = payload.month
    import_job.period_source = "user"
    import_job.period_conflict = False
    import_job.period_validated = True

    if payload.statement_type is not None:
        import_job.detected_statement_type = payload.statement_type
    if payload.as_of_date is not None:
        import_job.detected_as_of_date = payload.as_of_date
    if payload.period_start is not None:
        import_job.detected_period_start = payload.period_start
    if payload.period_end is not None:
        import_job.detected_period_end = payload.period_end
    if payload.timeframe is not None:
        import_job.detected_timeframe = payload.timeframe

    if import_job.period:
        import_job.period.label = payload.label.strip()
        import_job.period.year = payload.year
        if payload.statement_type:
            import_job.period.statement_type = payload.statement_type
        if payload.as_of_date:
            import_job.period.as_of_date = payload.as_of_date
        if payload.period_start:
            import_job.period.period_start = payload.period_start
        if payload.period_end:
            import_job.period.period_end = payload.period_end
        if payload.timeframe:
            import_job.period.timeframe = payload.timeframe

    db.commit()
    db.refresh(import_job)
    return import_job


@router.get("/{import_id}/sheets", response_model=SheetsResponse)
def get_import_sheets(import_id: int, db: Session = Depends(get_db)) -> SheetsResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return SheetsResponse(sheets=get_sheet_analysis(db, import_job))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{import_id}/sheets/{sheet_name}/preview", response_model=PreviewResponse)
def get_preview(
    import_id: int,
    sheet_name: str,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> PreviewResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return get_sheet_preview(import_job, sheet_name, db=db, limit=limit)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{import_id}/rows", response_model=ImportRowsResponse)
def get_import_rows(import_id: int, db: Session = Depends(get_db)) -> ImportRowsResponse:
    if db.get(FinancialImport, import_id) is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    rows = db.query(ImportRow).filter(ImportRow.source_import_id == import_id).all()
    return ImportRowsResponse(
        rows=[
            {
                "id": row.id,
                "source_sheet": row.source_sheet,
                "source_row": row.source_row,
                "original_code": row.original_code,
                "original_name": row.original_name,
                "normalized_name": row.normalized_name,
                "matched_account_id": row.matched_account_id,
                "match_type": row.match_type.value,
                "confidence": float(row.confidence) if row.confidence is not None else None,
                "status": row.status.value,
                "row_classification": row.row_classification.value,
            }
            for row in rows
        ],
        total=len(rows),
    )


@router.get("/{import_id}/issues", response_model=ImportRowsResponse)
def get_import_issues(import_id: int, db: Session = Depends(get_db)) -> ImportRowsResponse:
    if db.get(FinancialImport, import_id) is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    rows = (
        db.query(ImportRow)
        .filter(
            ImportRow.source_import_id == import_id,
            ImportRow.status.in_([
                RowStatus.NEEDS_REVIEW,
                RowStatus.UNKNOWN,
                RowStatus.NEW_ACCOUNT,
                RowStatus.ERROR,
            ]),
        )
        .all()
    )
    return ImportRowsResponse(
        rows=[
            {
                "id": row.id,
                "source_sheet": row.source_sheet,
                "source_row": row.source_row,
                "original_code": row.original_code,
                "original_name": row.original_name,
                "normalized_name": row.normalized_name,
                "matched_account_id": row.matched_account_id,
                "match_type": row.match_type.value,
                "confidence": float(row.confidence) if row.confidence is not None else None,
                "status": row.status.value,
                "row_classification": row.row_classification.value,
            }
            for row in rows
        ],
        total=len(rows),
    )


@router.patch("/{import_id}/rows/{row_id}", response_model=ImportResponse)
def review_import_row(import_id: int, row_id: int, payload: RowReviewUpdate, db: Session = Depends(get_db)) -> FinancialImport:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return review_row(
            db,
            import_job,
            row_id,
            payload.action,
            payload.account_id,
            payload.row_classification,
            payload.canonical_role,
            payload.ending_balance,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{import_id}/approve", response_model=ImportResponse)
def approve_uploaded_import(import_id: int, db: Session = Depends(get_db)) -> FinancialImport:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return approve_import(db, import_job)
    except AccountingValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ACCOUNTING_VALIDATION_FAILED",
                "validation": jsonable_encoder(error.validation),
            },
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{import_id}/sheets/{sheet_name}/approve", response_model=SheetApprovalResponse)
def approve_import_sheet(
    import_id: int,
    sheet_name: str,
    payload: SheetApprovalRequest,
    db: Session = Depends(get_db),
) -> SheetApprovalResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return approve_sheet(db, import_job, sheet_name, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
