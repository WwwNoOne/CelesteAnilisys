from app.domain.entities import Account
from app.domain.enums import AccountType


def test_account_code_keeps_leading_zeroes():
    account = Account(code="01", name="Activo")

    assert account.code == "01"


def test_account_keeps_original_and_normalized_names():
    account = Account(code="12010203", name=" Vehículos ", account_type=AccountType.ACTIVO)

    assert account.name == " Vehículos "
    assert account.normalized_name == "VEHICULOS"
    assert account.account_type is AccountType.ACTIVO


def test_same_name_can_exist_under_different_codes():
    production = Account(code="410415", name="Honorarios", account_type=AccountType.COSTO)
    administration = Account(code="420110", name="Honorarios", account_type=AccountType.GASTO)

    assert production.normalized_name == administration.normalized_name == "HONORARIOS"
    assert production.code != administration.code
