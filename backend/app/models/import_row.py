from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import MatchType, RowStatus

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.financial_import import FinancialImport


class ImportRow(Base):
    __tablename__ = "import_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_import_id: Mapped[int] = mapped_column(
        ForeignKey("financial_imports.id"), nullable=False
    )
    source_sheet: Mapped[str] = mapped_column(String(200), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
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

    source_import: Mapped["FinancialImport"] = relationship(back_populates="rows")
    matched_account: Mapped["Account | None"] = relationship(back_populates="import_rows")
