from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import MatchType, RowClassification, RowStatus

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.financial_import import FinancialImport
    from app.models.imported_statement import ImportedStatement


class ImportRow(Base):
    __tablename__ = "import_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_import_id: Mapped[int] = mapped_column(
        ForeignKey("financial_imports.id"), nullable=False
    )
    imported_statement_id: Mapped[int | None] = mapped_column(
        ForeignKey("imported_statements.id")
    )
    source_sheet: Mapped[str] = mapped_column(String(200), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text_column: Mapped[int | None] = mapped_column(Integer)
    source_amount_column: Mapped[int | None] = mapped_column(Integer)
    original_code: Mapped[str | None] = mapped_column(String(64))
    original_name: Mapped[str | None] = mapped_column(String(300))
    normalized_name: Mapped[str | None] = mapped_column(String(300))
    matched_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    match_type: Mapped[MatchType] = mapped_column(
        Enum(MatchType, native_enum=False), nullable=False, default=MatchType.NONE
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2))
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, native_enum=False), nullable=False, default=RowStatus.UNKNOWN
    )
    row_classification: Mapped[RowClassification] = mapped_column(
        Enum(RowClassification, native_enum=False),
        nullable=False,
        default=RowClassification.CUENTA,
    )
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    debits: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    credits: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    ending_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_import: Mapped["FinancialImport"] = relationship(back_populates="rows")
    imported_statement: Mapped["ImportedStatement | None"] = relationship(back_populates="rows")
    matched_account: Mapped["Account | None"] = relationship(back_populates="import_rows")
