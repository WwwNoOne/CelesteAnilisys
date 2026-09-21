from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.domain.enums import FinancialStatement


@dataclass(slots=True)
class SheetSnapshot:
    name: str
    rows: list[list[Any]]


@dataclass(slots=True)
class WorkbookSnapshot:
    path: Path
    sheets: list[SheetSnapshot]


@dataclass(slots=True)
class SheetTypeResult:
    sheet_name: str
    normalized_name: str
    sheet_type: FinancialStatement
    confidence: float


@dataclass(slots=True)
class HeaderDetection:
    row_index: int | None
    columns: dict[str, int] = field(default_factory=dict)
    confidence: float = 0
