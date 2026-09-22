from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Company
from app.schemas.comparison_api import (
    ComparisonRequest,
    ComparisonResponse,
    ComparisonStatementResponse,
)
from app.services.comparison_service import compare_statements, list_available_statements

router = APIRouter(prefix="/api/companies/{company_id}", tags=["comparisons"])


@router.get(
    "/comparison-statements",
    response_model=list[ComparisonStatementResponse],
)
def get_comparison_statements(
    company_id: int,
    statement_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ComparisonStatementResponse]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        return list_available_statements(db, company_id, statement_type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/comparisons", response_model=ComparisonResponse)
def create_comparison(
    company_id: int,
    payload: ComparisonRequest,
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        return compare_statements(db, company_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
