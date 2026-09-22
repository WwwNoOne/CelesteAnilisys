from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.imported_statement import ImportedStatement


class AccountBalance(Base):
    __tablename__ = "account_balances"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_id", "account_id", name="uq_balances_company_period_account"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    source_import_id: Mapped[int] = mapped_column(
        ForeignKey("financial_imports.id"), nullable=False
    )
    imported_statement_id: Mapped[int | None] = mapped_column(
        ForeignKey("imported_statements.id")
    )
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    debits: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    credits: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    ending_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    is_authoritative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_sheet: Mapped[str] = mapped_column(String(200), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="balances")
    imported_statement: Mapped["ImportedStatement | None"] = relationship(
        back_populates="balances"
    )
