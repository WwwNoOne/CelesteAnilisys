from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import CanonicalRole, RowClassification


class ImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    file_name: str
    status: str
    total_rows: int
    recognized_rows: int
    review_rows: int
    unknown_rows: int = 0
    new_accounts: int
    error_rows: int
    detected_period_label: str | None = None
    detected_period_year: int | None = None
    detected_period_month: int | None = None
    period_source: str | None = None
    period_validated: bool = False
    period_conflict: bool = False
    detected_statement_type: str | None = None
    detected_as_of_date: date | None = None
    detected_period_start: date | None = None
    detected_period_end: date | None = None
    detected_timeframe: str | None = None


class PeriodUpdate(BaseModel):
    label: str
    year: int
    month: int | None = None
    statement_type: str | None = None
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    timeframe: str | None = None


class SheetResponse(BaseModel):
    sheet_name: str
    normalized_name: str
    sheet_type: str
    confidence: float
    header_row: int | None = None
    header_columns: dict[str, int] = {}
    status: str = "PENDING_REVIEW"
    discard_reason: str | None = None
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    timeframe: str | None = None
    date_label: str | None = None
    total_rows: int = 0
    recognized_rows: int = 0
    review_rows: int = 0
    unknown_rows: int = 0
    error_rows: int = 0


class SheetsResponse(BaseModel):
    sheets: list[SheetResponse]


class SheetPreviewRow(BaseModel):
    source_row: int
    cells: list[Any]
    import_row_id: int | None = None
    status: str | None = None
    account_code: str | None = None
    account_name: str | None = None
    row_classification: str = "CUENTA"
    canonical_role: CanonicalRole | None = None
    ending_balance: Decimal | None = None
    source_text_column: int | None = None
    source_amount_column: int | None = None
    is_generated: bool = False


class PreviewResponse(BaseModel):
    sheet_name: str
    columns: list[str] = []
    rows: list[list[Any]]
    total_rows: int
    truncated: bool = False
    row_details: list[SheetPreviewRow] = []
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    timeframe: str | None = None
    date_label: str | None = None


class ImportRowsResponse(BaseModel):
    rows: list[dict[str, Any]]
    total: int


class RowReviewUpdate(BaseModel):
    action: Literal["match", "ignore", "classify", "update_financial_line"]
    account_id: int | None = None
    row_classification: RowClassification | None = None
    canonical_role: CanonicalRole | None = None
    ending_balance: Decimal | None = None


class SheetApprovalRequest(BaseModel):
    label: str | None = None
    year: int | None = None
    statement_type: str | None = None
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    timeframe: str | None = None
    overwrite: bool = False


class SheetApprovalResponse(BaseModel):
    success: bool
    sheet_name: str
    status: str
    balances_saved: int
    is_duplicate: bool = False
    duplicate_warning: str | None = None
    period_id: int | None = None
