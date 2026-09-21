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
