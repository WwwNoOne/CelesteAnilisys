from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    statement_type: str
    base_period_id: int
    comparison_period_id: int


class ComparisonStatementResponse(BaseModel):
    period_id: int
    statement_type: str
    label: str
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    duration_days: int | None = None


class ComparisonSourceResponse(BaseModel):
    import_id: int
    sheet_name: str
    source_row: int


class ComparisonRowResponse(BaseModel):
    key: str
    account_id: int | None = None
    code: str | None = None
    name: str
    level: int = 0
    base_value: Decimal | None = None
    comparison_value: Decimal | None = None
    absolute_change: Decimal | None = None
    percentage_change: Decimal | None = None
    change_status: str
    base_source: ComparisonSourceResponse | None = None
    comparison_source: ComparisonSourceResponse | None = None
    children: list["ComparisonRowResponse"] = Field(default_factory=list)


class ComparisonGroupResponse(ComparisonRowResponse):
    is_group: bool = True


class ComparisonResponse(BaseModel):
    statement_type: str
    base_statement: ComparisonStatementResponse
    comparison_statement: ComparisonStatementResponse
    warnings: list[str] = Field(default_factory=list)
    groups: list[ComparisonGroupResponse]
