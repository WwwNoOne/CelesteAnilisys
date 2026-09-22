from app.domain.entities import Account, AccountAlias
from app.domain.enums import AccountType, MatchType, RowStatus
from app.schemas.import_analysis import HeaderDetection, SheetSnapshot
from app.services.account_extraction_service import extract_account_candidates
from app.services.account_matching_service import AccountCatalog, match_account


def catalog() -> AccountCatalog:
    return AccountCatalog(
        accounts=[
            Account(code="12010203", name="Vehículos", account_type=AccountType.ACTIVO),
            Account(code="410415", name="Honorarios", account_type=AccountType.COSTO, parent_code="4104"),
            Account(code="420110", name="Honorarios", account_type=AccountType.GASTO, parent_code="4201"),
            Account(code="420112", name="Combustibles y Lubricantes", account_type=AccountType.GASTO),
        ],
        aliases=[AccountAlias(account_code="12010203", alias="Equipo de transporte")],
    )


def test_exact_code_has_priority_and_preserves_string_code():
    result = match_account(
        {"code": "01", "name": "Activo", "normalized_name": "ACTIVO"},
        AccountCatalog(accounts=[Account(code="01", name="Activo")]),
    )

    assert result.match_type is MatchType.EXACT_CODE
    assert result.status is RowStatus.MATCHED
    assert result.account is not None
    assert result.account.code == "01"


def test_same_name_with_different_codes_is_ambiguous():
    result = match_account(
        {"code": None, "name": "Honorarios", "normalized_name": "HONORARIOS"},
        catalog(),
    )

    assert result.match_type is MatchType.NONE
    assert result.status is RowStatus.NEEDS_REVIEW
    assert result.reason == "AMBIGUOUS"


def test_context_resolves_same_name_without_using_name_as_global_identity():
    result = match_account(
        {
            "code": None,
            "name": "Honorarios",
            "normalized_name": "HONORARIOS",
            "context_codes": ["4201"],
        },
        catalog(),
    )

    assert result.match_type is MatchType.CONTEXT
    assert result.status is RowStatus.MATCHED
    assert result.account is not None
    assert result.account.code == "420110"


def test_alias_can_resolve_a_unique_account():
    result = match_account(
        {"code": None, "name": "Equipo de transporte", "normalized_name": "EQUIPO DE TRANSPORTE"},
        catalog(),
    )

    assert result.match_type is MatchType.ALIAS
    assert result.status is RowStatus.MATCHED
    assert result.account is not None
    assert result.account.code == "12010203"


def test_fuzzy_match_is_only_a_review_suggestion():
    result = match_account(
        {"code": None, "name": "Combustibles y Lobricantes", "normalized_name": "COMBUSTIBLES Y LOBRICANTES"},
        catalog(),
    )

    assert result.match_type is MatchType.FUZZY
    assert result.status is RowStatus.NEEDS_REVIEW
    assert result.account is not None
    assert result.account.code == "420112"


def test_extraction_preserves_sheet_and_excel_row():
    sheet = SheetSnapshot(
        name="Balance de Comprobación",
        rows=[
            ["Código", "Cuenta"],
            ["12010203", "Vehículos"],
            [None, None],
        ],
    )
    header = HeaderDetection(row_index=0, columns={"code": 0, "account_name": 1}, confidence=1)

    candidates = extract_account_candidates(sheet, header)

    assert len(candidates) == 1
    assert candidates[0].code == "12010203"
    assert candidates[0].name == "Vehículos"
    assert candidates[0].sheet == "Balance de Comprobación"
    assert candidates[0].excel_row == 2


def test_extraction_splits_inline_code_and_name():
    sheet = SheetSnapshot(
        name="Balance",
        rows=[
            ["Cuentas", "Saldo"],
            ["110102  Bancos Nacionales", 15000],
        ],
    )
    header = HeaderDetection(
        row_index=0,
        columns={"account_name": 0, "ending_balance": 1},
        confidence=1,
    )
    candidates = extract_account_candidates(sheet, header)
    assert len(candidates) == 1
    assert candidates[0].code == "110102"
    assert candidates[0].name == "Bancos Nacionales"


def test_extraction_skips_metadata_and_signatures_in_report_layout():
    sheet = SheetSnapshot(
        name="Reporte",
        rows=[
            ["EMPRESA S.A. DE C.V.", None],
            ["BALANCE GENERAL AL 31 DE DICIEMBRE", None],
            ["(Valores expresados en dolares)", None],
            ["ACTIVOS", None],
            ["EFECTIVO Y EQUIVALENTES", 1200],
            ["TOTAL ACTIVO", 1200],
            ["GABRIEL PERDOMO RODAS", None],
            ["REPRESENTANTE LEGAL", None],
        ],
    )
    header = HeaderDetection(
        row_index=-1,
        columns={"account_name": 0, "ending_balance": 1},
        confidence=0.7,
        column_blocks=[{"account_name": 0, "ending_balance": 1, "amount_start": 1, "amount_end": 2}],
    )
    candidates = extract_account_candidates(sheet, header)
    names = [c.name for c in candidates]
    assert "EMPRESA S.A. DE C.V." not in names
    assert "BALANCE GENERAL AL 31 DE DICIEMBRE" not in names
    assert "GABRIEL PERDOMO RODAS" not in names
    assert "REPRESENTANTE LEGAL" not in names
    assert "EFECTIVO Y EQUIVALENTES" in names
    assert "TOTAL ACTIVO" in names
