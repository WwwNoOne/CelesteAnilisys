from app.normalizers.text_normalizer import normalize_account_name


def test_normalize_account_name_removes_accents_and_extra_spaces():
    assert normalize_account_name(" Gastos   de Administración ") == "GASTOS DE ADMINISTRACION"
    assert normalize_account_name("Vehículos") == "VEHICULOS"
    assert normalize_account_name("VEHÍCULOS") == "VEHICULOS"


def test_normalize_account_name_removes_invisible_characters_and_keeps_meaningful_punctuation():
    assert normalize_account_name("  Equipo\u200b & Transporte / Vehículos-Especiales  ") == (
        "EQUIPO & TRANSPORTE / VEHICULOS-ESPECIALES"
    )


def test_normalize_account_name_handles_none_as_empty_text():
    assert normalize_account_name(None) == ""
