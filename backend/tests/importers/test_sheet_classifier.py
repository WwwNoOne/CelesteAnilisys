from app.domain.enums import FinancialStatement
from app.importers.sheet_classifier import classify_sheet


def test_classifies_equivalent_financial_statement_names():
    assert classify_sheet("Balance General", []).sheet_type is FinancialStatement.ESTADO_SITUACION_FINANCIERA
    assert classify_sheet("Estado de Resultados", []).sheet_type is FinancialStatement.ESTADO_RESULTADOS
    assert classify_sheet("Pérdidas y Ganancias", []).sheet_type is FinancialStatement.ESTADO_RESULTADOS


def test_classifies_from_content_when_sheet_name_is_not_descriptive():
    rows = [
        ["Código", "Cuenta", "Saldo anterior", "Cargos", "Abonos", "Saldo actual"],
        ["1101", "Efectivo", 100, 20, 5, 115],
    ]

    result = classify_sheet("Hoja1", rows)

    assert result.sheet_type is FinancialStatement.BALANCE_COMPROBACION
    assert result.confidence > 0


def test_unknown_sheet_is_not_forced_into_a_financial_statement():
    result = classify_sheet("Notas internas", [["Texto", "Valor"]])

    assert result.sheet_type is FinancialStatement.DESCONOCIDO
    assert result.confidence == 0
