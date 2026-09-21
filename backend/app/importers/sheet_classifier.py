from collections.abc import Iterable
from typing import Any

from app.domain.enums import FinancialStatement
from app.normalizers.text_normalizer import normalize_account_name
from app.schemas.import_analysis import SheetTypeResult

_KEYWORDS: dict[FinancialStatement, tuple[str, ...]] = {
    FinancialStatement.BALANCE_COMPROBACION: (
        "BALANCE DE COMPROBACION",
        "BALANCE COMPROBACION",
        "CARGOS",
        "ABONOS",
        "SALDO ANTERIOR",
        "SALDO ACTUAL",
    ),
    FinancialStatement.ESTADO_SITUACION_FINANCIERA: (
        "ESTADO DE SITUACION FINANCIERA",
        "BALANCE GENERAL",
        "BALANCE DE SITUACION",
        "ACTIVOS",
        "PASIVOS",
        "PATRIMONIO",
    ),
    FinancialStatement.ESTADO_RESULTADOS: (
        "ESTADO DE RESULTADOS",
        "PERDIDAS Y GANANCIAS",
        "INGRESOS",
        "COSTOS",
        "GASTOS",
        "UTILIDAD",
    ),
    FinancialStatement.FLUJO_EFECTIVO: (
        "FLUJO DE EFECTIVO",
        "FLUJOS DE EFECTIVO",
        "ACTIVIDADES OPERATIVAS",
        "ACTIVIDADES DE INVERSION",
    ),
}


def classify_sheet(name: str, rows: list[list[Any]]) -> SheetTypeResult:
    normalized_name = normalize_account_name(name)
    normalized_content = list(_normalized_values(rows))
    scores = {
        statement: _score_statement(statement, normalized_name, normalized_content)
        for statement in _KEYWORDS
    }
    statement, best_score = max(scores.items(), key=lambda item: item[1])

    if best_score == 0:
        return SheetTypeResult(
            sheet_name=name,
            normalized_name=normalized_name,
            sheet_type=FinancialStatement.DESCONOCIDO,
            confidence=0,
        )

    confidence = min(0.99, round(0.45 + (best_score * 0.1), 2))
    return SheetTypeResult(
        sheet_name=name,
        normalized_name=normalized_name,
        sheet_type=statement,
        confidence=confidence,
    )


def _normalized_values(rows: list[list[Any]]) -> Iterable[str]:
    for row in rows[:40]:
        for value in row:
            if value is not None and str(value).strip():
                yield normalize_account_name(value)


def _score_statement(
    statement: FinancialStatement,
    normalized_name: str,
    normalized_content: list[str],
) -> int:
    score = 0
    for keyword in _KEYWORDS[statement]:
        if keyword in normalized_name:
            score += 3
        score += sum(1 for value in normalized_content if keyword in value)
    return score
