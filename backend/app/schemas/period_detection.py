from datetime import date

from pydantic import BaseModel


class PeriodDetection(BaseModel):
    label: str | None = None
    year: int | None = None
    month: int | None = None
    source: str | None = None
    confidence: float = 0
    conflict: bool = False
    statement_type: str | None = None
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    timeframe: str | None = None
