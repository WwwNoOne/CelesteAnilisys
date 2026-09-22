from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain.enums import FinancialStatement
from app.importers.header_detector import detect_header
from app.importers.sheet_classifier import classify_sheet
from app.normalizers.text_normalizer import normalize_account_name
from app.schemas.import_analysis import HeaderDetection, SheetSnapshot
from app.services.account_extraction_service import AccountCandidate, extract_account_candidates
from app.services.period_detection_service import detect_period, detect_sheet_temporal_info

_EXPLICIT_STATEMENT_TITLES: dict[FinancialStatement, tuple[str, ...]] = {
    FinancialStatement.ESTADO_SITUACION_FINANCIERA: (
        "BALANCE GENERAL",
        "ESTADO DE SITUACION FINANCIERA",
    ),
    FinancialStatement.ESTADO_RESULTADOS: (
        "ESTADO DE RESULTADOS",
        "PERDIDAS Y GANANCIAS",
    ),
    FinancialStatement.FLUJO_EFECTIVO: ("FLUJO DE EFECTIVO", "FLUJOS DE EFECTIVO"),
    FinancialStatement.BALANCE_COMPROBACION: ("BALANCE DE COMPROBACION",),
}


@dataclass(slots=True)
class SheetAnalysisDecision:
    sheet_name: str
    valid: bool
    statement_type: str
    confidence: float
    candidates: list[AccountCandidate] = field(default_factory=list)
    discard_reason: str | None = None
    period_label: str | None = None
    period_year: int | None = None
    period_month: int | None = None
    period_source: str | None = None
    period_conflict: bool = False
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    timeframe: str | None = None


def analyze_sheet(sheet: SheetSnapshot, file_name: str) -> SheetAnalysisDecision:
    classification = classify_sheet(sheet.name, sheet.rows)
    explicit_types = _explicit_statement_types(sheet.rows)
    if len(explicit_types) > 1:
        return SheetAnalysisDecision(
            sheet_name=sheet.name,
            valid=False,
            statement_type=FinancialStatement.DESCONOCIDO.value,
            confidence=0,
            discard_reason="Contiene más de un estado financiero",
        )

    header = detect_header(sheet.rows)
    if header.row_index is None:
        header = HeaderDetection(row_index=-1, confidence=0.2)
    candidates = extract_account_candidates(sheet, header)
    candidates_with_amount = [candidate for candidate in candidates if candidate.ending_balance is not None]
    if not candidates_with_amount:
        return SheetAnalysisDecision(
            sheet_name=sheet.name,
            valid=False,
            statement_type=classification.sheet_type.value,
            confidence=classification.confidence,
            discard_reason="No contiene cuentas con saldos",
        )
    if classification.sheet_type == FinancialStatement.DESCONOCIDO:
        return SheetAnalysisDecision(
            sheet_name=sheet.name,
            valid=False,
            statement_type=classification.sheet_type.value,
            confidence=classification.confidence,
            discard_reason="No se reconoce un estado financiero",
        )

    temporal = detect_sheet_temporal_info(sheet)
    if not temporal:
        fallback = detect_period(file_name, [sheet])
        temporal = {
            "date_label": fallback.label,
            "year": fallback.year,
            "month": fallback.month,
            "source": fallback.source,
            "as_of_date": fallback.as_of_date,
            "period_start": fallback.period_start,
            "period_end": fallback.period_end,
            "timeframe": fallback.timeframe,
        }
    return SheetAnalysisDecision(
        sheet_name=sheet.name,
        valid=True,
        statement_type=classification.sheet_type.value,
        confidence=classification.confidence,
        candidates=candidates,
        period_label=temporal.get("date_label"),
        period_year=temporal.get("year"),
        period_month=temporal.get("month"),
        period_source=temporal.get("source"),
        as_of_date=temporal.get("as_of_date"),
        period_start=temporal.get("period_start"),
        period_end=temporal.get("period_end"),
        timeframe=temporal.get("timeframe"),
    )


def _explicit_statement_types(rows: list[list[Any]]) -> set[FinancialStatement]:
    values = [
        normalize_account_name(value)
        for row in rows[:20]
        for value in row[:12]
        if isinstance(value, str) and value.strip()
    ]
    return {
        statement
        for statement, titles in _EXPLICIT_STATEMENT_TITLES.items()
        if any(title in value for title in titles for value in values)
    }
