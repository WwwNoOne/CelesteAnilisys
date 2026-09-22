from pydantic import BaseModel, ConfigDict


class PeriodCreate(BaseModel):
    label: str
    year: int


class PeriodResponse(PeriodCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CompanyCreate(BaseModel):
    name: str


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CompanyDetailResponse(CompanyResponse):
    periods: list[PeriodResponse] = []


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    code: str
    name: str
    normalized_name: str
    account_type: str | None = None
    statement: str = "BALANCE_GENERAL"
    statement_label: str = "Balance General"
    category: str = "General"
    hierarchy_path: str = ""


class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str = "ACTIVO"
    statement: str | None = None
    category: str | None = None
