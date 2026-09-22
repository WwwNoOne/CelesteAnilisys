from app.importers.header_detector import detect_header


def test_detects_header_after_title_and_blank_rows():
    rows = [
        ["Empresa de prueba", None, None, None],
        ["Balance de comprobación 2025", None, None, None],
        [None, None, None, None],
        ["Código de cuenta", "Nombre de cuenta", "Saldo anterior", "Cargos", "Abonos", "Saldo actual"],
    ]

    result = detect_header(rows)

    assert result.row_index == 3
    assert result.columns["code"] == 0
    assert result.columns["account_name"] == 1
    assert result.columns["opening_balance"] == 2
    assert result.columns["debits"] == 3
    assert result.columns["credits"] == 4
    assert result.columns["ending_balance"] == 5
    assert result.confidence == 1


def test_returns_no_header_when_no_financial_columns_are_found():
    result = detect_header([["Cliente", "Dirección"], ["A", "B"]])

    assert result.row_index is None
    assert result.columns == {}
    assert result.confidence == 0


def test_detects_statement_layout_without_explicit_headers():
    result = detect_header([
        ["Empresa", None, None, None],
        ["INGRESOS DE OPERACIÓN", None, None, 12000],
        ["INGRESOS POR SERVICIOS", None, 12000, None],
    ])

    assert result.row_index == -1
    assert result.columns["account_name"] == 0


def test_detects_dual_block_account_layout():
    rows = [
        ["Empresa S.A. de C.V.", None, None, None, None, None],
        ["Balance General al 31 de Diciembre", None, None, None, None, None],
        ["(Valores expresados en dolares)", None, None, None, None, None],
        ["ACTIVOS", None, None, None, "PASIVOS", None],
        ["EFECTIVO Y EQUIVALENTES", 1500, None, None, "CUENTAS POR PAGAR", 1200],
        ["CLIENTES", 3000, None, None, "PROVEEDORES", 800],
    ]
    result = detect_header(rows)
    assert result.row_index == -1
    assert len(result.column_blocks) == 2
    assert result.column_blocks[0]["account_name"] == 0
    assert result.column_blocks[1]["account_name"] == 4
