from decimal import Decimal

import pytest

from app.domain.enums import CanonicalRole, RowClassification
from app.services.statement_duplicate_service import (
    RoleDeclaration,
    resolve_role_declarations,
)


def declaration(
    role: str | None,
    value: str,
    classification: str,
    source_row: int,
) -> RoleDeclaration:
    return RoleDeclaration(
        canonical_role=CanonicalRole(role) if role else None,
        value=Decimal(value),
        classification=RowClassification(classification),
        source_row=source_row,
    )


def test_explicit_total_wins_without_adding_children():
    result = resolve_role_declarations(
        [
            declaration("ACTIVO", "50000", "TOTAL", 20),
            declaration(None, "20000", "CUENTA", 5),
            declaration(None, "30000", "CUENTA", 6),
        ],
        CanonicalRole.ACTIVO,
    )

    assert result.value == Decimal(50000)
    assert result.is_authoritative is True


def test_equal_duplicates_collapse_but_different_values_conflict():
    equal = resolve_role_declarations(
        [
            declaration("ACTIVO", "50000", "TOTAL", 20),
            declaration("ACTIVO", "50000", "TOTAL", 30),
        ],
        CanonicalRole.ACTIVO,
    )

    assert equal.duplicate_rows == [30]

    with pytest.raises(ValueError, match="saldos distintos"):
        resolve_role_declarations(
            [
                declaration("ACTIVO", "50000", "TOTAL", 20),
                declaration("ACTIVO", "51000", "TOTAL", 30),
            ],
            CanonicalRole.ACTIVO,
        )
