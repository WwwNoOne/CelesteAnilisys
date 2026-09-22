# Canonical Extraction and Accounting Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extraer líneas financieras por bloques `texto → saldo`, asignarlas a roles canónicos confirmados y bloquear la aprobación cuando falten componentes o no cuadren las ecuaciones contables.

**Architecture:** El extractor producirá bloques independientes del formato de columnas. El catálogo persistirá un rol canónico por cuenta y los saldos distinguirán totales autoritativos de detalles. Un servicio puro con `Decimal` devolverá validaciones explicables; FastAPI decidirá la aprobación y React solo presentará/corregirá datos.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Pydantic 2, pytest, Ruff, React 19, TypeScript, Vite, Vitest y Electron.

**Spec:** `docs/superpowers/specs/2026-09-22-canonical-extraction-and-accounting-validation-design.md`

## Global Constraints

- El nombre original del Excel es evidencia; la identidad final procede del catálogo confirmado.
- Las celdas vacías no cierran bloques; un texto nuevo sí.
- Una fila completamente vacía no genera candidatos, registros ni pendientes.
- Cero explícito es válido; ausencia de un componente bloquea.
- Totales explícitos son autoritativos y no se suman nuevamente con detalles.
- Las ecuaciones usan `Decimal` y tolerancia absoluta `0.01`.
- El aislamiento es por empresa, importación, hoja, estado y período.
- No existe omisión manual de una regla bloqueante.
- React no realiza aritmética contable autoritativa.

## Review Focus

- `texto | vacío | 0 | texto` conserva el cero en el primer bloque; Task 2 lo prueba.
- Un total explícito y sus hijas nunca duplican saldo aunque cambie el orden; Task 5 lo prueba.
- Empresas o períodos con roles iguales nunca se mezclan; Task 6 lo prueba.
- Una validación lenta no pinta errores tras cambiar de hoja; Task 8 lo prueba.
- Firmas, notas y filas visuales sin `import_row_id` no crean pendientes; Tasks 3 y 9 lo prueban.

---

### Task 1: Persistir roles canónicos y autoridad de totales

**Files:**
- Modify: `backend/app/domain/enums.py`
- Modify: `backend/app/models/account.py`
- Modify: `backend/app/models/account_balance.py`
- Create: `backend/alembic/versions/009_add_canonical_accounting_fields.py`
- Modify: `backend/app/schemas/company_api.py`
- Modify: `backend/app/api/companies.py`
- Test: `backend/tests/db/test_model_constraints.py`
- Create: `backend/tests/api/test_accounts_api.py`

**Interfaces:**
- Consumes: modelos y catálogo actuales.
- Produces: `CanonicalRole`, `Account.canonical_role`, `AccountBalance.is_authoritative` y campos HTTP homónimos.

- [ ] **Step 1: Escribir pruebas fallidas**

```python
def test_account_persists_optional_canonical_role(session):
    account = Account(company_id=1, code="TOTAL-ACTIVO", name="Activo",
                      account_type=AccountType.ACTIVO,
                      canonical_role=CanonicalRole.ACTIVO)
    session.add(account)
    session.commit()
    assert session.get(Account, account.id).canonical_role == CanonicalRole.ACTIVO

def test_create_account_returns_canonical_role():
    response = client.post("/api/companies/1/accounts", json={
        "code": "TOTAL-ACTIVO", "name": "Activo",
        "account_type": "ACTIVO", "canonical_role": "ACTIVO",
    })
    assert response.status_code == 201
    assert response.json()["canonical_role"] == "ACTIVO"
```

- [ ] **Step 2: Confirmar RED**

Run: `docker-compose exec api pytest tests/db/test_model_constraints.py tests/api/test_accounts_api.py -q`

Expected: FAIL porque enum y columnas no existen.

- [ ] **Step 3: Implementar enum y modelos**

```python
class CanonicalRole(StrEnum):
    ACTIVO = "ACTIVO"
    PASIVO = "PASIVO"
    PATRIMONIO = "PATRIMONIO"
    VENTAS = "VENTAS"
    COSTO_VENTAS = "COSTO_VENTAS"
    UTILIDAD_BRUTA = "UTILIDAD_BRUTA"
    GASTOS = "GASTOS"
    IMPUESTOS = "IMPUESTOS"
    RESULTADO_EJERCICIO = "RESULTADO_EJERCICIO"
```

`Account.canonical_role` será `Enum(CanonicalRole, native_enum=False), nullable=True`. `AccountBalance.is_authoritative` será booleano no nulo con valor inicial falso. La migración `009` añadirá `accounts.canonical_role VARCHAR(40)` y `account_balances.is_authoritative BOOLEAN NOT NULL DEFAULT false`; downgrade eliminará ambas.

- [ ] **Step 4: Extender catálogo HTTP**

```python
class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str = "ACTIVO"
    canonical_role: CanonicalRole | None = None

class AccountResponse(BaseModel):
    canonical_role: CanonicalRole | None = None
```

Crear/buscar cuentas copiará y devolverá el rol persistido, sin inferirlo otra vez del nombre.

- [ ] **Step 5: Migrar y confirmar GREEN**

Run: `docker-compose exec api alembic upgrade head`

Run: `docker-compose exec api pytest tests/db/test_model_constraints.py tests/api/test_accounts_api.py -q`

Run: `docker-compose exec api ruff check app/domain/enums.py app/models app/schemas/company_api.py app/api/companies.py tests/db/test_model_constraints.py tests/api/test_accounts_api.py`

- [ ] **Step 6: Commit**

```bash
git add backend/app/domain/enums.py backend/app/models/account.py backend/app/models/account_balance.py backend/alembic/versions/009_add_canonical_accounting_fields.py backend/app/schemas/company_api.py backend/app/api/companies.py backend/tests/db/test_model_constraints.py backend/tests/api/test_accounts_api.py
git commit -m "feat: persist canonical accounting roles"
```

---

### Task 2: Tokenizar filas en bloques texto–importe

**Files:**
- Create: `backend/app/services/row_block_extraction_service.py`
- Create: `backend/tests/services/test_row_block_extraction_service.py`

**Interfaces:**
- Consumes: `list[Any]` de una fila Excel.
- Produces: `RowBlock` y `extract_row_blocks(row) -> list[RowBlock]`.

- [ ] **Step 1: Escribir pruebas fallidas de patrones**

```python
def test_amount_belongs_to_previous_text_across_empty_cells():
    blocks = extract_row_blocks(["Ingresos", None, None, 12000, "Conciliación", None])
    assert [(b.text, b.amount) for b in blocks] == [
        ("Ingresos", Decimal("12000.00")), ("Conciliación", None),
    ]

def test_two_lateral_text_amount_blocks_are_independent():
    blocks = extract_row_blocks(["Activo", 50000, None, "Pasivo", None, 30000])
    assert [(b.text, b.amount) for b in blocks] == [
        ("Activo", Decimal("50000.00")), ("Pasivo", Decimal("30000.00")),
    ]

def test_explicit_zero_survives_and_empty_row_disappears():
    assert extract_row_blocks(["Costo", None, 0])[0].amount == Decimal("0.00")
    assert extract_row_blocks([None, "", None]) == []
```

- [ ] **Step 2: Confirmar RED**

Run: `docker-compose exec api pytest tests/services/test_row_block_extraction_service.py -q`

Expected: FAIL al importar el módulo.

- [ ] **Step 3: Implementar tokenizer mínimo**

```python
@dataclass(frozen=True, slots=True)
class RowBlock:
    text: str
    normalized_text: str
    amount: Decimal | None
    text_column: int
    amount_column: int | None

def extract_row_blocks(row: list[Any]) -> list[RowBlock]:
    blocks: list[RowBlock] = []
    current_text: tuple[str, int] | None = None
    current_amount: tuple[Decimal, int] | None = None

    def flush() -> None:
        nonlocal current_text, current_amount
        if current_text is not None:
            text, text_column = current_text
            blocks.append(RowBlock(
                text=text,
                normalized_text=normalize_account_name(text),
                amount=current_amount[0] if current_amount else None,
                text_column=text_column,
                amount_column=current_amount[1] if current_amount else None,
            ))
        current_text = None
        current_amount = None

    for column, value in enumerate(row):
        if isinstance(value, str) and value.strip():
            flush()
            current_text = (value.strip(), column)
        elif current_text is not None and current_amount is None and is_amount(value):
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
            current_amount = (amount, column)
    flush()
    return blocks

def is_amount(value: Any) -> TypeGuard[int | float | Decimal]:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
```

La implementación excluirá booleanos y cuantizará números con `Decimal("0.01")`.

- [ ] **Step 4: Añadir bordes**

```python
def test_number_before_text_is_not_assigned_forward():
    blocks = extract_row_blocks([2025, "Ventas", 10])
    assert [(b.text, b.amount) for b in blocks] == [("Ventas", Decimal("10.00"))]

def test_first_number_is_declared_balance_when_block_has_more_numbers():
    block = extract_row_blocks(["Cuenta", None, 15, 99])[0]
    assert (block.amount, block.amount_column) == (Decimal("15.00"), 2)
```

- [ ] **Step 5: Confirmar GREEN**

Run: `docker-compose exec api pytest tests/services/test_row_block_extraction_service.py -q`

Run: `docker-compose exec api ruff check app/services/row_block_extraction_service.py tests/services/test_row_block_extraction_service.py`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/row_block_extraction_service.py backend/tests/services/test_row_block_extraction_service.py
git commit -m "feat: extract financial row blocks"
```

---

### Task 3: Integrar bloques y eliminar pendientes fantasma

**Files:**
- Modify: `backend/app/services/account_extraction_service.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/tests/services/test_account_matching_service.py`
- Modify: `backend/tests/importers/test_real_workbooks.py`
- Modify: `src/renderer/import-review-state.ts`
- Modify: `src/renderer/pages/ImportReviewPage.tsx`
- Modify: `tests/unit/import-review-state.test.ts`

**Interfaces:**
- Consumes: `extract_row_blocks`.
- Produces: candidatos por bloque e `isPendingPreviewRow(row)`.

- [ ] **Step 1: Escribir pruebas backend fallidas**

```python
def test_report_layout_emits_two_lateral_candidates():
    sheet = SheetSnapshot(name="Balance", rows=[
        ["Activo", None, 50000, "Pasivo", None, 30000],
    ])
    header = HeaderDetection(row_index=-1, columns={}, confidence=.5)
    result = extract_account_candidates(sheet, header)
    assert [(c.name, c.ending_balance) for c in result] == [
        ("Activo", Decimal("50000.00")), ("Pasivo", Decimal("30000.00")),
    ]

def test_text_context_and_empty_rows_emit_no_candidates():
    sheet = SheetSnapshot(name="Balance", rows=[
        ["Activo", None, "Pasivo"], [None, None, None],
    ])
    assert extract_account_candidates(
        sheet, HeaderDetection(row_index=-1, columns={}, confidence=.5)
    ) == []
```

- [ ] **Step 2: Escribir prueba frontend fallida**

```typescript
it('does not count visual rows without import_row_id', () => {
  expect(isPendingPreviewRow({
    source_row: 1, cells: ['Título'], import_row_id: null, status: null,
    account_code: null, account_name: null, row_classification: 'CUENTA',
  })).toBe(false);
});
```

- [ ] **Step 3: Confirmar RED**

Run: `docker-compose exec api pytest tests/services/test_account_matching_service.py tests/importers/test_real_workbooks.py -q`

Run: `npm test -- tests/unit/import-review-state.test.ts`

- [ ] **Step 4: Integrar bloques en layouts de reporte**

Cuando `header.row_index < 0`, crear un candidato por `RowBlock` con importe. Descartar metadatos/firmas y bloques sin importe. Los balances de comprobación con encabezado explícito mantienen código, debe, haber y saldo actuales. Persistir también líneas `TOTAL`/`SUBTOTAL`; no omitirlas por no ser `CUENTA`.

- [ ] **Step 5: Implementar conteo real**

```typescript
export function isPendingPreviewRow(row: SheetPreviewRow): boolean {
  return row.import_row_id !== null
    && row.row_classification === 'CUENTA'
    && row.status !== 'MATCHED';
}
```

- [ ] **Step 6: Fijar regresión BENGALA**

```python
def test_bengala_2024_preserves_declared_lines():
    workbook = read_workbook(EXAMPLES_DIR / "2025-ER BENGALA.xlsx")
    sheet = next(item for item in workbook.sheets if item.name == "2024")
    by_name = {c.name: c for c in extract_account_candidates(sheet, detect_header(sheet.rows))}
    assert by_name["INGRESOS POR SERVICIOS"].ending_balance == Decimal("12000.00")
    assert by_name["GASTOS DE ADMINISTRACION"].ending_balance == Decimal("1041.57")
    assert by_name["UTILIDAD DEL EJERCICIO"].ending_balance == Decimal("5608.04")
```

- [ ] **Step 7: Confirmar GREEN**

Run: `docker-compose exec api pytest tests/services/test_account_matching_service.py tests/importers/test_real_workbooks.py tests/api/test_import_analysis.py tests/api/test_import_preview.py -q`

Run: `npm test -- tests/unit/import-review-state.test.ts`

Run: `docker-compose exec api ruff check app/services/account_extraction_service.py app/services/excel_import_service.py tests/services/test_account_matching_service.py tests/importers/test_real_workbooks.py`

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/account_extraction_service.py backend/app/services/excel_import_service.py backend/tests/services/test_account_matching_service.py backend/tests/importers/test_real_workbooks.py src/renderer/import-review-state.ts src/renderer/pages/ImportReviewPage.tsx tests/unit/import-review-state.test.ts
git commit -m "feat: extract report balances by row blocks"
```

---

### Task 4: Corregir cuenta, rol, clasificación y saldo

**Files:**
- Modify: `backend/app/schemas/import_api.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/api/imports.py`
- Modify: `backend/tests/api/test_import_review_api.py`
- Modify: `src/renderer/api.ts`
- Modify: `src/renderer/components/imports/RowReviewPanel.tsx`
- Modify: `src/renderer/pages/ImportReviewPage.tsx`
- Modify: `src/renderer/import-review-state.ts`
- Modify: `tests/unit/import-review-state.test.ts`

**Interfaces:**
- Consumes: `CanonicalRole` y líneas extraídas.
- Produces: acción `update_financial_line` atómica.

- [ ] **Step 1: Escribir prueba API fallida**

```python
def test_updates_account_role_classification_and_zero():
    response = client.patch("/api/imports/50/rows/202", json={
        "action": "update_financial_line", "account_id": 10,
        "row_classification": "TOTAL", "canonical_role": "COSTO_VENTAS",
        "ending_balance": "0.00",
    })
    assert response.status_code == 200
    with Session(test_engine) as session:
        row = session.get(ImportRow, 202)
        assert row.ending_balance == Decimal("0.00")
        assert row.row_classification == RowClassification.TOTAL
        assert session.get(Account, 10).canonical_role == CanonicalRole.COSTO_VENTAS
```

- [ ] **Step 2: Confirmar RED**

Run: `docker-compose exec api pytest tests/api/test_import_review_api.py::test_updates_account_role_classification_and_zero -q`

- [ ] **Step 3: Extender contrato y servicio**

```python
class RowReviewUpdate(BaseModel):
    action: Literal["match", "ignore", "classify", "update_financial_line"]
    account_id: int | None = None
    row_classification: RowClassification | None = None
    canonical_role: CanonicalRole | None = None
    ending_balance: Decimal | None = None
```

La acción exige cuenta, clasificación, rol y saldo; acepta cero; conserva `original_name`, hoja y fila; actualiza la cuenta seleccionada y recalcula contadores.

- [ ] **Step 4: Añadir tipos y formulario frontend**

```typescript
export type CanonicalRole = 'ACTIVO' | 'PASIVO' | 'PATRIMONIO'
  | 'VENTAS' | 'COSTO_VENTAS' | 'UTILIDAD_BRUTA'
  | 'GASTOS' | 'IMPUESTOS' | 'RESULTADO_EJERCICIO';
```

`RowReviewPanel` mostrará select de rol e input numérico `step="0.01"`. `reviewImportRow` recibirá objeto tipado, no parámetros posicionales.

- [ ] **Step 5: Probar serialización de cero y GREEN**

```typescript
it('keeps explicit zero in correction payload', () => {
  expect(buildFinancialLineUpdate(10, 'TOTAL', 'COSTO_VENTAS', '0').ending_balance)
    .toBe('0');
});
```

Run: `docker-compose exec api pytest tests/api/test_import_review_api.py -q`

Run: `npm test -- tests/unit/import-review-state.test.ts`

Run: `npm run build:renderer`

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/import_api.py backend/app/services/excel_import_service.py backend/app/api/imports.py backend/tests/api/test_import_review_api.py src/renderer/api.ts src/renderer/components/imports/RowReviewPanel.tsx src/renderer/pages/ImportReviewPage.tsx src/renderer/import-review-state.ts tests/unit/import-review-state.test.ts
git commit -m "feat: edit canonical financial lines"
```

---

### Task 5: Persistir totales sin doble conteo y detectar duplicados

**Files:**
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/services/statement_duplicate_service.py`
- Create: `backend/tests/services/test_authoritative_balance_service.py`
- Modify: `backend/tests/api/test_sheet_approval_api.py`

**Interfaces:**
- Consumes: roles, clasificación e `is_authoritative`.
- Produces: `resolve_role_declarations(rows, role)` y saldos persistidos sin duplicación.

- [ ] **Step 1: Escribir pruebas fallidas**

```python
def declaration(role, value, classification, source_row):
    return RoleDeclaration(
        canonical_role=CanonicalRole(role) if role else None,
        value=Decimal(value),
        classification=RowClassification(classification),
        source_row=source_row,
    )

def test_explicit_total_wins_without_adding_children():
    result = resolve_role_declarations([
        declaration("ACTIVO", "50000", "TOTAL", 20),
        declaration(None, "20000", "CUENTA", 5),
        declaration(None, "30000", "CUENTA", 6),
    ], CanonicalRole.ACTIVO)
    assert result.value == Decimal("50000")
    assert result.is_authoritative is True

def test_equal_duplicates_collapse_but_different_values_conflict():
    equal = resolve_role_declarations([
        declaration("ACTIVO", "50000", "TOTAL", 20),
        declaration("ACTIVO", "50000", "TOTAL", 30),
    ], CanonicalRole.ACTIVO)
    assert equal.duplicate_rows == [30]
    with pytest.raises(ValueError, match="saldos distintos"):
        resolve_role_declarations([
            declaration("ACTIVO", "50000", "TOTAL", 20),
            declaration("ACTIVO", "51000", "TOTAL", 30),
        ], CanonicalRole.ACTIVO)
```

- [ ] **Step 2: Confirmar RED**

Run: `docker-compose exec api pytest tests/services/test_authoritative_balance_service.py tests/api/test_sheet_approval_api.py -q`

- [ ] **Step 3: Implementar resolución determinista**

Crear `RoleDeclarationResolution(value, is_authoritative, primary_row, duplicate_rows)`. Ordenar por `source_row, id`. `TOTAL`/`SUBTOTAL` con rol son declaraciones autoritativas; una `CUENTA` lo será solo si la cuenta de catálogo representa directamente el rol agregado.

- [ ] **Step 4: Persistir líneas asignadas**

`approve_sheet` considerará `CUENTA`, `SUBTOTAL` y `TOTAL` cuando tengan cuenta y saldo. `_persist_balances` copiará autoridad y rechazará valores distintos para misma cuenta/período antes de sobrescribir.

- [ ] **Step 5: Confirmar GREEN**

Run: `docker-compose exec api pytest tests/services/test_authoritative_balance_service.py tests/api/test_sheet_approval_api.py -q`

Run: `docker-compose exec api ruff check app/services/excel_import_service.py app/services/statement_duplicate_service.py tests/services/test_authoritative_balance_service.py tests/api/test_sheet_approval_api.py`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/excel_import_service.py backend/app/services/statement_duplicate_service.py backend/tests/services/test_authoritative_balance_service.py backend/tests/api/test_sheet_approval_api.py
git commit -m "feat: persist authoritative financial totals"
```

---

### Task 6: Implementar motor puro de ecuaciones

**Files:**
- Create: `backend/app/schemas/accounting_validation.py`
- Create: `backend/app/services/accounting_validation_service.py`
- Create: `backend/tests/services/test_accounting_validation_service.py`
- Modify: `backend/app/domain/enums.py`

**Interfaces:**
- Consumes: saldos por rol/hoja/período.
- Produces: `validate_balance_equation`, `validate_income_statement_equations`, `validate_import_accounting`.

- [ ] **Step 1: Escribir pruebas fallidas de balance**

```python
def component(value, row_id=1):
    return AccountingComponent(
        value=Decimal(str(value)),
        row_ids=[row_id],
        sources=[],
        explicit=True,
    )

def test_explicit_zero_is_valid_but_missing_component_blocks():
    valid = validate_balance_equation({
        CanonicalRole.ACTIVO: component("100"),
        CanonicalRole.PASIVO: component("0"),
        CanonicalRole.PATRIMONIO: component("100"),
    })
    assert valid.status == ValidationStatus.VALID
    missing = validate_balance_equation({
        CanonicalRole.ACTIVO: component("100"),
        CanonicalRole.PATRIMONIO: component("100"),
    })
    assert missing.status == ValidationStatus.MISSING_COMPONENTS
    assert missing.missing_roles == [CanonicalRole.PASIVO]
```

- [ ] **Step 2: Escribir pruebas fallidas de resultados, tolerancia y aislamiento**

```python
@pytest.mark.parametrize("result", [Decimal("20"), Decimal("-20")])
def test_income_statement_supports_profit_and_signed_loss(result):
    gross = Decimal("100")
    rules = validate_income_statement_equations({
        CanonicalRole.VENTAS: component("150"),
        CanonicalRole.COSTO_VENTAS: component("50"),
        CanonicalRole.UTILIDAD_BRUTA: component(gross),
        CanonicalRole.GASTOS: component(gross - result),
        CanonicalRole.IMPUESTOS: component("0"),
        CanonicalRole.RESULTADO_EJERCICIO: component(result),
    })
    assert all(rule.status == ValidationStatus.VALID for rule in rules)

def test_two_cents_difference_is_mismatch():
    result = validate_balance_equation({
        CanonicalRole.ACTIVO: component("100.02"),
        CanonicalRole.PASIVO: component("60"),
        CanonicalRole.PATRIMONIO: component("40"),
    })
    assert result.status == ValidationStatus.MISMATCH
    assert result.difference == Decimal("0.02")
```

Añadir fixture de dos empresas/períodos con mismos roles y comprobar que `validate_import_accounting(session, import_id)` solo devuelve fuentes de la empresa/período solicitado.

- [ ] **Step 3: Confirmar RED**

Run: `docker-compose exec api pytest tests/services/test_accounting_validation_service.py -q`

- [ ] **Step 4: Definir contratos**

```python
class ValidationStatus(StrEnum):
    VALID = "VALID"
    MISMATCH = "MISMATCH"
    MISSING_COMPONENTS = "MISSING_COMPONENTS"
    DUPLICATE_CONFLICT = "DUPLICATE_CONFLICT"

class AccountingRuleResult(BaseModel):
    rule_id: str
    label: str
    status: ValidationStatus
    left_value: Decimal | None
    right_value: Decimal | None
    difference: Decimal | None
    tolerance: Decimal = Decimal("0.01")
    missing_roles: list[CanonicalRole] = Field(default_factory=list)
    row_ids: list[int] = Field(default_factory=list)
    sources: list[AccountingSource] = Field(default_factory=list)

class AccountingValidationResponse(BaseModel):
    valid: bool
    rules: list[AccountingRuleResult]
```

- [ ] **Step 5: Implementar ecuaciones**

La diferencia será `left - right`; `VALID` cuando `abs(difference) <= Decimal("0.01")`. Consultar exclusivamente empresa/importación/hoja/período y preferir declaraciones autoritativas.

- [ ] **Step 6: Confirmar GREEN**

Run: `docker-compose exec api pytest tests/services/test_accounting_validation_service.py -q`

Run: `docker-compose exec api ruff check app/schemas/accounting_validation.py app/services/accounting_validation_service.py tests/services/test_accounting_validation_service.py`

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/accounting_validation.py backend/app/services/accounting_validation_service.py backend/tests/services/test_accounting_validation_service.py backend/app/domain/enums.py
git commit -m "feat: validate canonical accounting equations"
```

---

### Task 7: Exponer validación y bloquear aprobación

**Files:**
- Modify: `backend/app/api/imports.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/schemas/import_api.py`
- Create: `backend/tests/api/test_accounting_validation_api.py`
- Modify: `backend/tests/api/test_import_review_api.py`

**Interfaces:**
- Consumes: `validate_import_accounting`.
- Produces: `GET /api/imports/{id}/accounting-validation` y bloqueo HTTP 422 estructurado.

- [ ] **Step 1: Escribir pruebas fallidas**

```python
def seed_validation_import(session, *, import_id, values):
    job = FinancialImport(
        id=import_id, company_id=1, period_id=1,
        file_name=f"{import_id}.xlsx", status=ImportStatus.READY_FOR_REVIEW,
        period_validated=True, approved_sheets=["Balance"],
    )
    session.add(job)
    for offset, (role, value) in enumerate(values.items(), start=1):
        account = Account(
            id=import_id * 10 + offset, company_id=1,
            code=f"{import_id}-{offset}", name=role.value,
            canonical_role=role,
        )
        session.add(account)
        session.flush()
        session.add(AccountBalance(
            company_id=1, period_id=1, account_id=account.id,
            source_import_id=import_id, ending_balance=Decimal(value),
            source_sheet="Balance", source_row=offset,
            is_authoritative=True,
        ))
    session.commit()

def test_endpoint_returns_missing_roles():
    with Session(test_engine) as session:
        seed_validation_import(session, import_id=90, values={
            CanonicalRole.ACTIVO: "100", CanonicalRole.PASIVO: "40",
        })
    response = client.get("/api/imports/90/accounting-validation")
    assert response.status_code == 200
    assert response.json()["rules"][0]["missing_roles"] == ["PATRIMONIO"]

def test_approve_returns_structured_validation_failure():
    with Session(test_engine) as session:
        seed_validation_import(session, import_id=91, values={
            CanonicalRole.ACTIVO: "100", CanonicalRole.PASIVO: "40",
            CanonicalRole.PATRIMONIO: "50",
        })
    response = client.post("/api/imports/91/approve")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ACCOUNTING_VALIDATION_FAILED"
```

- [ ] **Step 2: Confirmar RED**

Run: `docker-compose exec api pytest tests/api/test_accounting_validation_api.py -q`

- [ ] **Step 3: Implementar endpoint y error**

```python
@router.get("/{import_id}/accounting-validation",
            response_model=AccountingValidationResponse)
def get_accounting_validation(import_id: int, db: Session = Depends(get_db)):
    _require_import(db, import_id)
    return validate_import_accounting(db, import_id)
```

Crear `AccountingValidationError(validation)`. `approve_import` validará después de hojas guardadas y antes de cambiar estado; API devolverá `detail.code` y `detail.validation`.

- [ ] **Step 4: Probar aprobación válida con impuesto cero**

```python
def test_approve_accepts_valid_income_statement_with_zero_tax():
    with Session(test_engine) as session:
        seed_validation_import(session, import_id=92, values={
            CanonicalRole.VENTAS: "150", CanonicalRole.COSTO_VENTAS: "50",
            CanonicalRole.UTILIDAD_BRUTA: "100", CanonicalRole.GASTOS: "80",
            CanonicalRole.IMPUESTOS: "0", CanonicalRole.RESULTADO_EJERCICIO: "20",
        })
    response = client.post("/api/imports/92/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
```

- [ ] **Step 5: Confirmar GREEN y regresión backend**

Run: `docker-compose exec api pytest tests/api/test_accounting_validation_api.py tests/api/test_import_review_api.py tests/api/test_sheet_approval_api.py -q`

Run: `docker-compose exec api pytest -q`

Run: `docker-compose exec api ruff check .`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/imports.py backend/app/services/excel_import_service.py backend/app/schemas/import_api.py backend/tests/api/test_accounting_validation_api.py backend/tests/api/test_import_review_api.py
git commit -m "feat: block invalid financial approvals"
```

---

### Task 8: Mostrar ecuaciones y filas rojas

**Files:**
- Modify: `src/renderer/api.ts`
- Modify: `src/renderer/import-review-state.ts`
- Create: `src/renderer/components/imports/AccountingValidationPanel.tsx`
- Modify: `src/renderer/components/imports/PreviewTable.tsx`
- Modify: `src/renderer/pages/ImportReviewPage.tsx`
- Modify: `src/renderer/styles.css`
- Modify: `tests/unit/import-review-state.test.ts`

**Interfaces:**
- Consumes: respuesta de validación Task 7.
- Produces: panel, `collectInvalidRowIds`, solicitud protegida contra respuestas obsoletas.

- [ ] **Step 1: Escribir pruebas fallidas**

```typescript
it('collects rows only from blocking rules', () => {
  const ids = collectInvalidRowIds({ valid: false, rules: [
    { rule_id: 'balance', status: 'MISMATCH', row_ids: [1, 2, 3] },
    { rule_id: 'gross', status: 'VALID', row_ids: [4, 5] },
  ] } as AccountingValidationResponse);
  expect(ids).toEqual(new Set([1, 2, 3]));
});

it('invalidates old validation after changing sheets', () => {
  const tracker = createRequestTracker();
  const old = tracker.begin();
  const current = tracker.begin();
  expect(tracker.isCurrent(old)).toBe(false);
  expect(tracker.isCurrent(current)).toBe(true);
});
```

- [ ] **Step 2: Confirmar RED**

Run: `npm test -- tests/unit/import-review-state.test.ts`

- [ ] **Step 3: Añadir tipos, cliente y helpers**

```typescript
export function getAccountingValidation(importId: number) {
  return request<AccountingValidationResponse>(
    `/api/imports/${importId}/accounting-validation`,
  );
}

export function collectInvalidRowIds(validation: AccountingValidationResponse | null) {
  return new Set(validation?.rules
    .filter((rule) => rule.status !== 'VALID')
    .flatMap((rule) => rule.row_ids) ?? []);
}
```

- [ ] **Step 4: Crear panel explicable**

Para `MISMATCH`, mostrar fórmula, ambos lados y diferencia. Para `MISSING_COMPONENTS`, listar roles y “debe existir explícitamente, aunque su saldo sea 0”. Tarjetas bloqueantes usan `role="alert"`.

- [ ] **Step 5: Integrar resaltado y recálculo**

`PreviewTable` recibe `invalidRowIds` y aplica `financial-row-invalid`. ImportReviewPage recarga al corregir/guardar, descarta solicitudes obsoletas al cambiar hoja y renombra el botón **Validar y aprobar**. El backend sigue siendo autoridad final.

- [ ] **Step 6: Confirmar GREEN y build**

Run: `npm test -- tests/unit/import-review-state.test.ts`

Run: `npm test`

Run: `npm run build`

- [ ] **Step 7: Commit**

```bash
git add src/renderer/api.ts src/renderer/import-review-state.ts src/renderer/components/imports/AccountingValidationPanel.tsx src/renderer/components/imports/PreviewTable.tsx src/renderer/pages/ImportReviewPage.tsx src/renderer/styles.css tests/unit/import-review-state.test.ts
git commit -m "feat: present blocking accounting validation"
```

---

### Task 9: Validar libros reales y documentar

**Files:**
- Modify: `backend/tests/importers/test_real_workbooks.py`
- Create: `backend/tests/integration/test_real_workbook_accounting_flow.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Tasks 1–8.
- Produces: regresión real, documentación y evidencia integral.

- [ ] **Step 1: Escribir integración real fallida**

```python
def test_bengala_extracts_both_years_with_declared_lines(tmp_path):
    source = Path("data/examples/2025-ER BENGALA.xlsx")
    copied = tmp_path / source.name
    shutil.copy2(source, copied)
    workbook = read_workbook(copied)
    assert {sheet.name for sheet in workbook.sheets} == {"2024", "2025"}
    extracted = {
        sheet.name: extract_account_candidates(sheet, detect_header(sheet.rows))
        for sheet in workbook.sheets
    }
    by_name = {candidate.name: candidate for candidate in extracted["2024"]}
    assert by_name["INGRESOS POR SERVICIOS"].ending_balance == Decimal("12000.00")
    assert all(candidate.ending_balance is not None for candidate in extracted["2024"])
```

La prueba copiará el libro a un directorio temporal y no modificará `data/examples`. No exigirá roles inventados: una asignación ausente debe producir `MISSING_COMPONENTS`.

- [ ] **Step 2: Confirmar RED**

Run: `docker-compose exec api pytest tests/integration/test_real_workbook_accounting_flow.py -q`

- [ ] **Step 3: Corregir únicamente adaptadores descubiertos**

No relajar fórmulas ni bloqueos. Cualquier variante nueva de firma/metadato tendrá primero una prueba específica en `test_real_workbooks.py`.

- [ ] **Step 4: Documentar flujo**

```markdown
### Validación contable antes de aprobar

1. Revisa texto original, cuenta de catálogo, rol y saldo.
2. Declara con saldo 0 cualquier componente obligatorio sin movimiento.
3. Guarda todas las hojas financieras.
4. Pulsa **Validar y aprobar**.
5. Corrige las filas rojas hasta que las ecuaciones cuadren.

Los nombres del Excel son evidencia; las ecuaciones usan roles confirmados.
```

- [ ] **Step 5: Verificación backend**

Run: `docker-compose exec api alembic upgrade head`

Run: `docker-compose exec api pytest -q`

Run: `docker-compose exec api ruff check .`

- [ ] **Step 6: Verificación frontend**

Run: `npm test`

Run: `npm run build`

Run: `git diff --check`

- [ ] **Step 7: Prueba manual controlada**

1. Cargar `2025-ER BENGALA.xlsx` en una base desechable.
2. Confirmar que vacíos, títulos y firmas no son pendientes.
3. Confirmar/corregir cuentas y roles de 2024 y 2025.
4. Verificar que rol ausente bloquea y cero explícito permite validar.
5. Alterar temporalmente un saldo y comprobar ecuación/fila roja.
6. Restaurar saldo, validar y aprobar.
7. Confirmar Archivos y Comparaciones sin regresiones.

- [ ] **Step 8: Commit**

```bash
git add backend/tests/importers/test_real_workbooks.py backend/tests/integration/test_real_workbook_accounting_flow.py README.md
git commit -m "test: verify canonical real workbook flow"
```

- [ ] **Step 9: Revisión final**

Usar `superpowers:requesting-code-review` desde el commit base con foco en asociación texto–saldo, cero explícito, doble conteo, aislamiento, bloqueo backend y regresiones del importador.
