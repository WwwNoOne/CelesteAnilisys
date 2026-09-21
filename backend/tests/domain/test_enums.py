from app.domain.enums import AccountType, MatchType, RowStatus


def test_account_type_does_not_treat_balance_as_an_account_type():
    assert {account_type.value for account_type in AccountType} == {
        "ACTIVO",
        "PASIVO",
        "PATRIMONIO",
        "INGRESO",
        "COSTO",
        "GASTO",
        "OTRO",
    }


def test_matching_and_row_status_values_are_explicit():
    assert MatchType.EXACT_CODE.value == "EXACT_CODE"
    assert MatchType.FUZZY.value == "FUZZY"
    assert RowStatus.NEEDS_REVIEW.value == "NEEDS_REVIEW"
