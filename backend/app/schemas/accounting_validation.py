from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import CanonicalRole, ValidationStatus


class AccountingSource(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    canonical_role: CanonicalRole
    value: Decimal
    sheet: str
    source_row: int
    row_id: int | None = None


class AccountingComponent(BaseModel):
    value: Decimal
    row_ids: list[int] = Field(default_factory=list)
    sources: list[AccountingSource] = Field(default_factory=list)
    explicit: bool


class AccountingRuleResult(BaseModel):
    rule_id: str
    label: str
    status: ValidationStatus
    left_value: Decimal | None
    right_value: Decimal | None
    difference: Decimal | None
    tolerance: Decimal = Decimal("0.01")
    missing_roles: list[CanonicalRole] = Field(default_factory=list)
    row_ids: list[int] = Field(default_factory=list)
    sources: list[AccountingSource] = Field(default_factory=list)


class AccountingValidationResponse(BaseModel):
    valid: bool
    rules: list[AccountingRuleResult]
