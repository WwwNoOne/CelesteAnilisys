from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeGuard

from app.normalizers.text_normalizer import normalize_account_name


@dataclass(frozen=True, slots=True)
class RowBlock:
    text: str
    normalized_text: str
    amount: Decimal | None
    text_column: int
    amount_column: int | None


def is_amount(value: Any) -> TypeGuard[int | float | Decimal]:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def extract_row_blocks(row: list[Any]) -> list[RowBlock]:
    blocks: list[RowBlock] = []
    current_text: tuple[str, int] | None = None
    current_amount: tuple[Decimal, int] | None = None

    def flush() -> None:
        nonlocal current_text, current_amount
        if current_text is not None:
            text, text_column = current_text
            blocks.append(
                RowBlock(
                    text=text,
                    normalized_text=normalize_account_name(text),
                    amount=current_amount[0] if current_amount else None,
                    text_column=text_column,
                    amount_column=current_amount[1] if current_amount else None,
                )
            )
        current_text = None
        current_amount = None

    for column, value in enumerate(row):
        if isinstance(value, str) and value.strip():
            flush()
            current_text = (value.strip(), column)
        elif current_text is not None and current_amount is None and is_amount(value):
            current_amount = (Decimal(str(value)).quantize(Decimal("0.01")), column)

    flush()
    return blocks
