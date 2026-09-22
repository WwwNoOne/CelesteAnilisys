import re
import unicodedata
from typing import Any

METADATA_PATTERNS = [
    re.compile(r"(s\.a\.|s\.a\. de c\.v\.|sociedad anonima|limitada|ltda|inc\b|corp\b)", re.IGNORECASE),
    re.compile(r"\b(balance general|estado de resultados|flujo de efectivo|cambio en el patrimonio|balance de comprobacion)\b", re.IGNORECASE),
    re.compile(r"\b(valores expresados|expresado en|us dolares|dolares de los estados unidos)\b", re.IGNORECASE),
    re.compile(r"\b(representante legal|contador general|auditor|revisor fiscal|lic\.)\b", re.IGNORECASE),
    re.compile(r"^(del \d|al \d|\(\s*valores)", re.IGNORECASE),
]


def is_metadata_or_signature(text: Any) -> bool:
    if text is None:
        return False
    value = str(text).strip()
    return any(pattern.search(value) for pattern in METADATA_PATTERNS)


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
