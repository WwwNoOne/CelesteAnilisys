from typing import Any

from pydantic import BaseModel, ConfigDict


class ImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    status: str
    total_rows: int
    recognized_rows: int
    review_rows: int
    new_accounts: int
    error_rows: int


class SheetResponse(BaseModel):
    sheet_name: str
    normalized_name: str
    sheet_type: str
    confidence: float
    header_row: int | None
    header_columns: dict[str, int]


class SheetsResponse(BaseModel):
    sheets: list[SheetResponse]


class PreviewResponse(BaseModel):
    sheet_name: str
    rows: list[list[Any]]
    total_rows: int


class ImportRowsResponse(BaseModel):
    rows: list[dict[str, Any]]
    total: int


class RowReviewUpdate(BaseModel):
    action: str
    account_id: int | None = None
