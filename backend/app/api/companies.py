from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.enums import AccountType
from app.models import Account, Company, FinancialImport, Period
from app.normalizers.text_normalizer import normalize_account_name
from app.schemas.company_api import (
    AccountCreate,
    AccountResponse,
    CompanyCreate,
    CompanyDetailResponse,
    CompanyResponse,
    PeriodCreate,
    PeriodResponse,
)
from app.schemas.import_api import ImportResponse
from app.services.catalog_hierarchy_service import (
    ensure_company_standard_catalog,
    get_account_hierarchy_info,
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


@router.get("/{company_id}/accounts", response_model=list[AccountResponse])
def list_company_accounts(
    company_id: int,
    query: str | None = None,
    statement: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[AccountResponse]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Ensure base catalog exists for hierarchy navigation
    ensure_company_standard_catalog(db, company_id)

    q = db.query(Account).filter(Account.company_id == company_id)
    if query and query.strip():
        search = f"%{query.strip()}%"
        q = q.filter(
            (Account.code.ilike(search))
            | (Account.name.ilike(search))
            | (Account.normalized_name.ilike(search))
        )
    accounts = q.order_by(Account.code).all()

    results: list[AccountResponse] = []
    for acc in accounts:
        h_info = get_account_hierarchy_info(acc)
        if statement and statement != "ALL" and h_info["statement"] != statement:
            continue
        if category and category != "ALL" and h_info["category"] != category:
            continue
        results.append(
            AccountResponse(
                id=acc.id,
                company_id=acc.company_id,
                code=acc.code,
                name=acc.name,
                normalized_name=acc.normalized_name,
                account_type=acc.account_type.value if hasattr(acc.account_type, "value") else str(acc.account_type),
                statement=h_info["statement"],
                statement_label=h_info["statement_label"],
                category=h_info["category"],
                hierarchy_path=h_info["hierarchy_path"],
            )
        )
    return results


@router.post("/{company_id}/accounts", response_model=AccountResponse, status_code=201)
def create_company_account(
    company_id: int,
    payload: AccountCreate,
    db: Session = Depends(get_db),
) -> AccountResponse:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    code = payload.code.strip()
    name = payload.name.strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail="Código y nombre son obligatorios")
    acc_type = (
        AccountType(payload.account_type)
        if payload.account_type in AccountType.__members__
        else AccountType.ACTIVO
    )
    account = Account(
        company_id=company_id,
        code=code,
        name=name,
        normalized_name=normalize_account_name(name),
        account_type=acc_type,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    h_info = get_account_hierarchy_info(account)
    return AccountResponse(
        id=account.id,
        company_id=account.company_id,
        code=account.code,
        name=account.name,
        normalized_name=account.normalized_name,
        account_type=account.account_type.value if hasattr(account.account_type, "value") else str(account.account_type),
        statement=h_info["statement"],
        statement_label=h_info["statement_label"],
        category=h_info["category"],
        hierarchy_path=h_info["hierarchy_path"],
    )


@router.get("/{company_id}/imports", response_model=list[ImportResponse])
def list_company_imports(
    company_id: int,
    db: Session = Depends(get_db),
) -> list[FinancialImport]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return (
        db.query(FinancialImport)
        .filter(FinancialImport.company_id == company_id)
        .order_by(FinancialImport.created_at.desc())
        .all()
    )
