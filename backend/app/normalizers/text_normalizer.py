import unicodedata
from typing import Any


def normalize_account_name(text: Any) -> str:
    """Return a stable lookup value without changing the source account name."""
    if text is None:
        return ""

    string_value = str(text).strip().upper()
    decomposed = unicodedata.normalize("NFKD", string_value)
    without_accents = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    without_invisible = "".join(
        character
        for character in without_accents
        if unicodedata.category(character) not in {"Cc", "Cf"}
    )
    return " ".join(without_invisible.split())
