from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.enums import RowStatus
from app.models import FinancialImport, ImportRow
from app.schemas.import_api import (
    ImportResponse,
    ImportRowsResponse,
    PreviewResponse,
    RowReviewUpdate,
    SheetsResponse,
)
from app.services.excel_import_service import (
    analyze_import,
    approve_import,
    create_import,
    get_sheet_analysis,
    get_sheet_preview,
    review_row,
)

router = APIRouter(prefix="/api/imports", tags=["imports"])


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


@router.get("/{import_id}/sheets", response_model=SheetsResponse)
def get_import_sheets(import_id: int, db: Session = Depends(get_db)) -> SheetsResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return SheetsResponse(sheets=get_sheet_analysis(import_job))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{import_id}/sheets/{sheet_name}/preview", response_model=PreviewResponse)
def get_preview(import_id: int, sheet_name: str, db: Session = Depends(get_db)) -> PreviewResponse:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        rows = get_sheet_preview(import_job, sheet_name)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return PreviewResponse(sheet_name=sheet_name, rows=rows, total_rows=len(rows))


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
        return review_row(db, import_job, row_id, payload.action, payload.account_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{import_id}/approve", response_model=ImportResponse)
def approve_uploaded_import(import_id: int, db: Session = Depends(get_db)) -> FinancialImport:
    import_job = db.get(FinancialImport, import_id)
    if import_job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    try:
        return approve_import(db, import_job)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
