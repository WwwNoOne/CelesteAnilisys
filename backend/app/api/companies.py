from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Company, Period
from app.schemas.company_api import (
    CompanyCreate,
    CompanyDetailResponse,
    CompanyResponse,
    PeriodCreate,
    PeriodResponse,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    return db.query(Company).order_by(Company.name).all()


@router.post("", response_model=CompanyResponse, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre de la empresa es obligatorio")
    company = Company(name=name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyDetailResponse)
def get_company(company_id: int, db: Session = Depends(get_db)) -> CompanyDetailResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    periods = db.query(Period).order_by(Period.year.desc()).all()
    return CompanyDetailResponse(id=company.id, name=company.name, periods=periods)


@router.post("/{company_id}/periods", response_model=PeriodResponse, status_code=201)
def create_period(company_id: int, payload: PeriodCreate, db: Session = Depends(get_db)) -> Period:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    period = Period(label=payload.label.strip(), year=payload.year)
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.get("/{company_id}/periods", response_model=list[PeriodResponse])
def list_periods(company_id: int, db: Session = Depends(get_db)) -> list[Period]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return db.query(Period).order_by(Period.year.desc()).all()
