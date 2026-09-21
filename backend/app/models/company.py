from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.financial_import import FinancialImport


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="company")
    imports: Mapped[list["FinancialImport"]] = relationship(back_populates="company")
