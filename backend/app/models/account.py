from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import AccountNature, AccountType, CanonicalRole, FinancialStatement
from app.normalizers.text_normalizer import normalize_account_name

if TYPE_CHECKING:
    from app.models.account_alias import AccountAlias
    from app.models.account_balance import AccountBalance
    from app.models.company import Company
    from app.models.import_row import ImportRow


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_accounts_company_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False), nullable=False, default=AccountType.OTRO
    )
    canonical_role: Mapped[CanonicalRole | None] = mapped_column(
        Enum(CanonicalRole, native_enum=False), nullable=True
    )
    nature: Mapped[AccountNature] = mapped_column(
        Enum(AccountNature, native_enum=False), nullable=False, default=AccountNature.OTRA
    )
    level: Mapped[int | None] = mapped_column(Integer)
    parent_code: Mapped[str | None] = mapped_column(String(64))
    financial_statement: Mapped[FinancialStatement] = mapped_column(
        Enum(FinancialStatement, native_enum=False),
        nullable=False,
        default=FinancialStatement.DESCONOCIDO,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="accounts")
    aliases: Mapped[list["AccountAlias"]] = relationship(back_populates="account")
    balances: Mapped[list["AccountBalance"]] = relationship(back_populates="account")
    import_rows: Mapped[list["ImportRow"]] = relationship(back_populates="matched_account")

    def __init__(self, **kwargs):
        name = kwargs.get("name")
        if name is not None and "normalized_name" not in kwargs:
            kwargs["normalized_name"] = normalize_account_name(name)
        super().__init__(**kwargs)
