from dataclasses import dataclass, field

from app.domain.enums import (
    AccountNature,
    AccountType,
    FinancialStatement,
)
from app.normalizers.text_normalizer import normalize_account_name


@dataclass(slots=True)
class Account:
    code: str
    name: str
    account_type: AccountType = AccountType.OTRO
    nature: AccountNature = AccountNature.OTRA
    level: int | None = None
    parent_code: str | None = None
    financial_statement: FinancialStatement = FinancialStatement.DESCONOCIDO
    normalized_name: str = field(init=False)

    def __post_init__(self) -> None:
        self.code = str(self.code)
        self.name = str(self.name)
        self.normalized_name = normalize_account_name(self.name)


@dataclass(slots=True)
class AccountAlias:
    account_code: str
    alias: str
    normalized_alias: str = field(init=False)

    def __post_init__(self) -> None:
        self.account_code = str(self.account_code)
        self.normalized_alias = normalize_account_name(self.alias)
