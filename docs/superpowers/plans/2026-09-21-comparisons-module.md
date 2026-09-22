# Comparisons Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar Comparaciones para seleccionar manualmente dos estados financieros aprobados de una empresa y mostrar variaciones por grupos, cuentas y subcuentas.

**Architecture:** FastAPI expondrá una consulta de estados disponibles y una operación de comparación calculada al momento. Un servicio de dominio concentrará identidad temporal, compatibilidad, unión por `account_id`, jerarquía y cálculos; React consumirá respuestas ya normalizadas y se limitará a selección, estados de pantalla y presentación jerárquica.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL/SQLite de pruebas, Pydantic, React, TypeScript, Vite, Vitest y Electron.

**Spec:** `docs/superpowers/specs/2026-09-21-comparisons-module-design.md`

## Global Constraints

- Comparar exactamente dos estados aprobados de la misma empresa por operación.
- Permitir cualquier cantidad de períodos históricos en los selectores.
- Usar `as_of_date` para Balance y `period_start`/`period_end` para Estado de Resultados.
- Tratar `BALANCE_GENERAL` y `ESTADO_SITUACION_FINANCIERA` como el mismo tipo funcional.
- Calcular siempre período posterior menos período base anterior.
- Emparejar cuentas por `account_id`, nunca solo por texto original.
- Mostrar subcuentas como detalle desplegable sin duplicarlas en los totales.
- No persistir comparaciones ni crear tablas o migraciones.
- No implementar Dashboard automático, ratios, análisis vertical, tendencias, pronósticos ni exportaciones.
- Mantener la paleta y los patrones visuales actuales de Celeste Analysis.
- Mantener toda regla financiera fuera de los componentes React.

## Review Focus

- Una fila con `ending_balance=None` no debe convertirse en cero; Task 1 fija `Sin base comparable`.
- Períodos con el mismo año pero fechas distintas deben conservar identidades separadas; Task 2 lo prueba con dos balances de 2025.
- Un `period_id` de otra empresa no debe filtrarse a través de `Period`, que carece de `company_id`; Task 2 prueba el aislamiento a través de `AccountBalance.company_id`.
- Una cuenta padre y sus descendientes con saldo no deben sumarse simultáneamente; Task 3 prueba la regla de padre autoritativo.
- Una respuesta lenta que llega después de cambiar los selectores no debe reemplazar el resultado vigente; Task 6 prueba el descarte mediante identificador de solicitud.

---

## Mapa de archivos

### Backend

- Crear `backend/app/schemas/comparison_api.py`: contratos HTTP y tipos de respuesta.
- Crear `backend/app/services/comparison_service.py`: consulta, validación, agrupación y cálculo.
- Crear `backend/app/api/comparisons.py`: endpoints finos y traducción de errores de dominio.
- Modificar `backend/app/api/router.py`: registrar el router.
- Crear `backend/tests/services/test_comparison_service.py`: reglas puras y consultas de servicio.
- Crear `backend/tests/api/test_comparisons_api.py`: contrato HTTP, aislamiento y errores.

### Frontend

- Modificar `src/renderer/api.ts`: tipos y llamadas del módulo.
- Crear `src/renderer/comparison-state.ts`: selección cronológica, formato y estados derivados puros.
- Crear `src/renderer/pages/ComparisonPage.tsx`: coordinación de consultas y estado.
- Crear `src/renderer/components/comparisons/StatementTypeSelector.tsx`: selector de estado.
- Crear `src/renderer/components/comparisons/FinancialPeriodSelector.tsx`: selector de período.
- Crear `src/renderer/components/comparisons/ComparisonWarnings.tsx`: advertencias accesibles.
- Crear `src/renderer/components/comparisons/ComparisonTable.tsx`: tabla y expansión jerárquica.
- Modificar `src/renderer/components/ContextHeader.tsx`: permitir ocultar controles sin duplicar encabezado.
- Modificar `src/renderer/main.tsx`: montar la página y navegar a Archivos.
- Modificar `src/renderer/navigation.ts`: centralizar cuándo se muestran los controles globales.
- Modificar `src/renderer/styles.css`: estilos aislados con prefijo `comparison-`.
- Crear `tests/unit/comparison-state.test.ts`: reglas puras de selección y formato.
- Crear `tests/unit/comparison-page-state.test.ts`: estado vacío, advertencias y solicitudes obsoletas.
- Modificar `tests/unit/navigation.test.ts`: confirmar que `/comparisons` sigue en el menú.

### Documentación

- Modificar `README.md`: documentar el flujo manual de Comparaciones y comandos de verificación.

---

### Task 1: Contratos y cálculo numérico seguro

**Files:**
- Create: `backend/app/schemas/comparison_api.py`
- Create: `backend/app/services/comparison_service.py`
- Test: `backend/tests/services/test_comparison_service.py`

**Interfaces:**
- Consumes: `Decimal`, `date`, `AccountBalance`, `Account`, `Period`, `FinancialImport`.
- Produces: `ComparisonRequest`, `ComparisonStatementResponse`, `ComparisonRowResponse`, `ComparisonGroupResponse`, `ComparisonResponse`, `calculate_change(base_value, comparison_value)`.

- [ ] **Step 1: Escribir pruebas fallidas para las reglas numéricas**

Crear las pruebas iniciales:

```python
from decimal import Decimal

from app.services.comparison_service import calculate_change


def test_calculate_change_uses_later_minus_base_and_absolute_denominator():
    result = calculate_change(Decimal("-100"), Decimal("-75"))
    assert result.absolute_change == Decimal("25")
    assert result.percentage_change == Decimal("25")
    assert result.change_status == "CALCULATED"


def test_calculate_change_handles_zero_missing_and_null_without_nan():
    assert calculate_change(Decimal("0"), Decimal("10")).change_status == "NEW"
    assert calculate_change(Decimal("0"), Decimal("0")).change_status == "UNCHANGED"
    assert calculate_change(None, Decimal("10"), base_present=False).change_status == "NEW"
    assert calculate_change(Decimal("10"), None, comparison_present=False).change_status == "REMOVED"
    assert calculate_change(None, Decimal("10"), base_present=True).change_status == "NO_BASE"
```

- [ ] **Step 2: Ejecutar las pruebas y confirmar el fallo esperado**

Run: `docker-compose exec api pytest tests/services/test_comparison_service.py -q`

Expected: FAIL al importar `app.services.comparison_service`.

- [ ] **Step 3: Definir los esquemas de respuesta**

Implementar contratos con nombres estables:

```python
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    statement_type: str
    base_period_id: int
    comparison_period_id: int


class ComparisonStatementResponse(BaseModel):
    period_id: int
    statement_type: str
    label: str
    as_of_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    duration_days: int | None = None


class ComparisonSourceResponse(BaseModel):
    import_id: int
    sheet_name: str
    source_row: int


class ComparisonRowResponse(BaseModel):
    key: str
    account_id: int | None = None
    code: str | None = None
    name: str
    level: int = 0
    base_value: Decimal | None = None
    comparison_value: Decimal | None = None
    absolute_change: Decimal | None = None
    percentage_change: Decimal | None = None
    change_status: str
    base_source: ComparisonSourceResponse | None = None
    comparison_source: ComparisonSourceResponse | None = None
    children: list["ComparisonRowResponse"] = Field(default_factory=list)


class ComparisonGroupResponse(ComparisonRowResponse):
    is_group: bool = True


class ComparisonResponse(BaseModel):
    statement_type: str
    base_statement: ComparisonStatementResponse
    comparison_statement: ComparisonStatementResponse
    warnings: list[str] = Field(default_factory=list)
    groups: list[ComparisonGroupResponse]
```

- [ ] **Step 4: Implementar el cálculo mínimo con `Decimal`**

Agregar un resultado interno inmutable y la función:

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ChangeResult:
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    change_status: str


def calculate_change(
    base_value: Decimal | None,
    comparison_value: Decimal | None,
    *,
    base_present: bool = True,
    comparison_present: bool = True,
) -> ChangeResult:
    if not base_present:
        return ChangeResult(comparison_value, None, "NEW")
    if not comparison_present:
        absolute = -base_value if base_value is not None else None
        return ChangeResult(absolute, None, "REMOVED")
    if base_value is None or comparison_value is None:
        return ChangeResult(None, None, "NO_BASE")
    absolute = comparison_value - base_value
    if base_value == 0:
        status = "UNCHANGED" if comparison_value == 0 else "NEW"
        return ChangeResult(absolute, None, status)
    percentage = (absolute / abs(base_value)) * Decimal("100")
    return ChangeResult(absolute, percentage, "CALCULATED")
```

- [ ] **Step 5: Ejecutar las pruebas del cálculo**

Run: `docker-compose exec api pytest tests/services/test_comparison_service.py -q`

Expected: PASS para los casos de signo, cero, ausencia y nulo.

- [ ] **Step 6: Ejecutar Ruff y crear commit**

Run: `docker-compose exec api ruff check app/schemas/comparison_api.py app/services/comparison_service.py tests/services/test_comparison_service.py`

```bash
git add backend/app/schemas/comparison_api.py backend/app/services/comparison_service.py backend/tests/services/test_comparison_service.py
git commit -m "feat: add comparison contracts and safe change math"
```

---

### Task 2: Descubrimiento de estados y compatibilidad temporal

**Files:**
- Modify: `backend/app/services/comparison_service.py`
- Test: `backend/tests/services/test_comparison_service.py`

**Interfaces:**
- Consumes: `Session`, `ImportStatus.APPROVED`, `AccountBalance.company_id`, `Period`.
- Produces: `normalize_statement_type(value)`, `list_available_statements(db, company_id, statement_type=None)`, `validate_statement_pair(base, comparison, requested_type)`.

- [ ] **Step 1: Agregar fixtures explícitos para dos empresas y tipos de estado**

Crear un helper de prueba que inserte períodos, importaciones aprobadas y saldos. Debe incluir dos balances dentro de 2025 con fechas distintas y un período de otra empresa:

```python
def seed_available_statements(session: Session) -> None:
    session.add_all([
        Company(id=2, name="Otra empresa"),
        Period(id=10, label="31 Ene 2025", year=2025, statement_type="BALANCE_GENERAL", as_of_date=date(2025, 1, 31)),
        Period(id=11, label="31 Dic 2025", year=2025, statement_type="ESTADO_SITUACION_FINANCIERA", as_of_date=date(2025, 12, 31)),
        Period(id=12, label="2024", year=2024, statement_type="ESTADO_RESULTADOS", period_start=date(2024, 1, 1), period_end=date(2024, 12, 31)),
        Period(id=13, label="2025", year=2025, statement_type="ESTADO_RESULTADOS", period_start=date(2025, 1, 1), period_end=date(2025, 9, 30)),
    ])
```

Añadir importaciones y saldos de empresa 1 para 10–13, más un saldo de empresa 2 que reutilice `period_id=11`. Incluir también una importación `READY_FOR_REVIEW` para demostrar que no aparece.

- [ ] **Step 2: Escribir pruebas fallidas de listado e identidad**

```python
def test_list_available_statements_keeps_same_year_dates_separate():
    with Session(test_engine) as session:
        seed_available_statements(session)
        items = list_available_statements(session, 1, "BALANCE_GENERAL")
    assert [item.period_id for item in items] == [11, 10]
    assert [item.as_of_date for item in items] == [date(2025, 12, 31), date(2025, 1, 31)]


def test_list_available_statements_is_scoped_through_company_balances():
    with Session(test_engine) as session:
        seed_available_statements(session)
        company_one = list_available_statements(session, 1)
        company_two = list_available_statements(session, 2)
    assert {item.period_id for item in company_one} != {item.period_id for item in company_two}


def test_unapproved_import_is_not_available():
    with Session(test_engine) as session:
        seed_available_statements(session)
        items = list_available_statements(session, 1)
    assert all(item.period_id != 99 for item in items)
```

- [ ] **Step 3: Ejecutar el archivo y comprobar el fallo**

Run: `docker-compose exec api pytest tests/services/test_comparison_service.py -q`

Expected: FAIL porque `list_available_statements` aún no existe.

- [ ] **Step 4: Implementar normalización, consulta y etiquetas**

Usar una consulta que parta de `AccountBalance` y una el resto:

```python
BALANCE_TYPES = {"BALANCE_GENERAL", "ESTADO_SITUACION_FINANCIERA"}


def normalize_statement_type(value: str | None) -> str:
    if value in BALANCE_TYPES:
        return "BALANCE_GENERAL"
    if value == "ESTADO_RESULTADOS":
        return value
    raise ValueError("Tipo de estado financiero no soportado")


def list_available_statements(
    db: Session,
    company_id: int,
    statement_type: str | None = None,
) -> list[ComparisonStatementResponse]:
    rows = (
        db.query(Period)
        .join(AccountBalance, AccountBalance.period_id == Period.id)
        .join(FinancialImport, FinancialImport.id == AccountBalance.source_import_id)
        .filter(
            AccountBalance.company_id == company_id,
            FinancialImport.company_id == company_id,
            FinancialImport.status == ImportStatus.APPROVED,
        )
        .distinct()
        .all()
    )
    items = [_statement_response(period) for period in rows]
    if statement_type:
        normalized = normalize_statement_type(statement_type)
        items = [item for item in items if item.statement_type == normalized]
    return sorted(items, key=_statement_sort_key, reverse=True)
```

Las funciones privadas construirán etiquetas españolas sin depender de la configuración regional del sistema y calcularán `duration_days` de forma inclusiva.

- [ ] **Step 5: Agregar pruebas de compatibilidad y advertencia**

```python
def test_results_with_different_duration_returns_warning():
    base = statement(period_id=12, start=date(2024, 1, 1), end=date(2024, 12, 31))
    later = statement(period_id=13, start=date(2025, 1, 1), end=date(2025, 9, 30))
    warnings = validate_statement_pair(base, later, "ESTADO_RESULTADOS")
    assert warnings == [
        "Los períodos seleccionados tienen diferente duración. "
        "La comparación porcentual puede no ser directamente equivalente."
    ]


def test_validation_rejects_mixed_same_and_reversed_periods():
    with pytest.raises(ValueError, match="mismo estado"):
        validate_statement_pair(balance_2024, balance_2024, "BALANCE_GENERAL")
    with pytest.raises(ValueError, match="tipos diferentes"):
        validate_statement_pair(balance_2024, results_2025, "BALANCE_GENERAL")
    with pytest.raises(ValueError, match="anterior"):
        validate_statement_pair(balance_2025, balance_2024, "BALANCE_GENERAL")
```

- [ ] **Step 6: Implementar `validate_statement_pair` y ejecutar pruebas**

Comparar `as_of_date` para Balance y la tupla `(period_start, period_end)` para Resultados. No corregir ni intercambiar selecciones.

Run: `docker-compose exec api pytest tests/services/test_comparison_service.py -q`

Expected: PASS para consulta, orden, aislamiento y compatibilidad.

- [ ] **Step 7: Ejecutar Ruff y crear commit**

Run: `docker-compose exec api ruff check app/services/comparison_service.py tests/services/test_comparison_service.py`

```bash
git add backend/app/services/comparison_service.py backend/tests/services/test_comparison_service.py
git commit -m "feat: discover compatible financial statements"
```

---

### Task 3: Unión por cuenta, jerarquía y prevención de doble conteo

**Files:**
- Modify: `backend/app/services/comparison_service.py`
- Test: `backend/tests/services/test_comparison_service.py`

**Interfaces:**
- Consumes: `list_available_statements`, `validate_statement_pair`, `calculate_change`, `get_account_hierarchy_info`.
- Produces: `compare_statements(db, company_id, request) -> ComparisonResponse`.

- [ ] **Step 1: Escribir pruebas fallidas de unión por `account_id`**

```python
def test_compare_joins_different_source_names_by_account_id():
    with Session(test_engine) as session:
        seed_comparison_pair(session, base_name="GASTOS DE ADMINISTRACION", later_name="Gastos administrativos")
        result = compare_statements(
            session,
            1,
            ComparisonRequest(
                statement_type="ESTADO_RESULTADOS",
                base_period_id=20,
                comparison_period_id=21,
            ),
        )
    rows = flatten_rows(result.groups)
    account_rows = [row for row in rows if row.account_id == 501]
    assert len(account_rows) == 1
    assert account_rows[0].base_value == Decimal("100")
    assert account_rows[0].comparison_value == Decimal("125")
```

Agregar otra prueba donde una cuenta solo existe en el período posterior y otra desaparece; verificar `NEW` y `REMOVED`.

- [ ] **Step 2: Escribir la prueba fallida de padre autoritativo**

```python
def test_parent_balance_is_authoritative_when_children_also_have_balances():
    with Session(test_engine) as session:
        seed_parent_and_children(
            session,
            parent_base=Decimal("1000"),
            child_base=[Decimal("600"), Decimal("400")],
            parent_later=Decimal("1200"),
            child_later=[Decimal("700"), Decimal("500")],
        )
        result = compare_statements(session, 1, balance_request(30, 31))
    fixed_assets = next(group for group in result.groups if group.key == "ACTIVO_NO_CORRIENTE")
    assert fixed_assets.base_value == Decimal("1000")
    assert fixed_assets.comparison_value == Decimal("1200")
    assert len(fixed_assets.children) >= 2
```

- [ ] **Step 3: Ejecutar y verificar el fallo**

Run: `docker-compose exec api pytest tests/services/test_comparison_service.py -q`

Expected: FAIL porque `compare_statements` no está implementado.

- [ ] **Step 4: Implementar carga de saldos y unión completa**

Crear un registro interno por saldo:

```python
@dataclass(frozen=True, slots=True)
class BalanceRecord:
    account: Account
    value: Decimal | None
    source: ComparisonSourceResponse


def _load_period_balances(
    db: Session,
    company_id: int,
    period_id: int,
) -> dict[int, BalanceRecord]:
    rows = (
        db.query(AccountBalance, Account)
        .join(Account, Account.id == AccountBalance.account_id)
        .join(FinancialImport, FinancialImport.id == AccountBalance.source_import_id)
        .filter(
            AccountBalance.company_id == company_id,
            Account.company_id == company_id,
            AccountBalance.period_id == period_id,
            FinancialImport.status == ImportStatus.APPROVED,
        )
        .all()
    )
    return {
        account.id: BalanceRecord(
            account=account,
            value=balance.ending_balance,
            source=ComparisonSourceResponse(
                import_id=balance.source_import_id,
                sheet_name=balance.source_sheet,
                source_row=balance.source_row,
            ),
        )
        for balance, account in rows
    }
```

Unir `set(base) | set(comparison)` y construir una sola fila por identificador.

- [ ] **Step 5: Implementar clasificación y árbol jerárquico**

Definir claves ordenadas por tipo de estado. Resolver primero `parent_code`, después la metadata de `get_account_hierarchy_info`, y finalmente `SIN_CLASIFICAR`.

Aplicar esta función al sumar ramas:

```python
def _authoritative_value(node: AccountNode, side: str) -> Decimal | None:
    own = node.base_value if side == "base" else node.comparison_value
    if own is not None:
        return own
    child_values = [_authoritative_value(child, side) for child in node.children]
    available = [value for value in child_values if value is not None]
    return sum(available, Decimal("0")) if available else None
```

No agregar `SIN_CLASIFICAR` a totales de Balance o Resultados.

- [ ] **Step 6: Implementar `compare_statements`**

La función debe:

1. Obtener ambos estados desde la lista disponible de la empresa.
2. Rechazar identificadores ausentes antes de cargar saldos.
3. Validar tipo y orden.
4. Cargar y unir saldos por `account_id`.
5. Construir grupos en orden estable.
6. Calcular cambios de detalles y grupos con `calculate_change`.
7. Devolver advertencias de duración.

- [ ] **Step 7: Ejecutar pruebas y revisar casos numéricos**

Run: `docker-compose exec api pytest tests/services/test_comparison_service.py -q`

Expected: PASS, incluyendo padre autoritativo, cuenta nueva, cuenta removida, negativos, nulos y nombres de origen distintos.

- [ ] **Step 8: Ejecutar Ruff y crear commit**

Run: `docker-compose exec api ruff check app/services/comparison_service.py tests/services/test_comparison_service.py`

```bash
git add backend/app/services/comparison_service.py backend/tests/services/test_comparison_service.py
git commit -m "feat: compare normalized account hierarchies"
```

---

### Task 4: API de Comparaciones

**Files:**
- Create: `backend/app/api/comparisons.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/api/test_comparisons_api.py`

**Interfaces:**
- Consumes: `list_available_statements`, `compare_statements`, `ComparisonRequest`.
- Produces: los dos endpoints definidos por la especificación.

- [ ] **Step 1: Escribir pruebas HTTP fallidas**

```python
def test_lists_only_approved_company_statements():
    seed_api_comparison_data()
    response = client.get("/api/companies/1/comparison-statements?statement_type=BALANCE_GENERAL")
    assert response.status_code == 200
    assert [item["period_id"] for item in response.json()] == [31, 30]


def test_compares_two_approved_periods():
    seed_api_comparison_data()
    response = client.post(
        "/api/companies/1/comparisons",
        json={
            "statement_type": "BALANCE_GENERAL",
            "base_period_id": 30,
            "comparison_period_id": 31,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["base_statement"]["period_id"] == 30
    assert body["comparison_statement"]["period_id"] == 31


def test_rejects_cross_company_or_mixed_statement_ids():
    seed_api_comparison_data()
    response = client.post(
        "/api/companies/1/comparisons",
        json={
            "statement_type": "BALANCE_GENERAL",
            "base_period_id": 30,
            "comparison_period_id": 88,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Uno de los estados no está disponible para esta empresa"
```

- [ ] **Step 2: Ejecutar y confirmar 404 por rutas inexistentes**

Run: `docker-compose exec api pytest tests/api/test_comparisons_api.py -q`

Expected: FAIL con 404.

- [ ] **Step 3: Crear un router fino**

```python
router = APIRouter(prefix="/api/companies/{company_id}", tags=["comparisons"])


@router.get("/comparison-statements", response_model=list[ComparisonStatementResponse])
def get_comparison_statements(
    company_id: int,
    statement_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ComparisonStatementResponse]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        return list_available_statements(db, company_id, statement_type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/comparisons", response_model=ComparisonResponse)
def create_comparison(
    company_id: int,
    payload: ComparisonRequest,
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        return compare_statements(db, company_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
```

Registrar `comparisons_router` en `backend/app/api/router.py`.

- [ ] **Step 4: Ejecutar pruebas API y backend completo**

Run: `docker-compose exec api pytest tests/api/test_comparisons_api.py -q`

Run: `docker-compose exec api pytest -q`

Expected: todos los tests pasan; el flujo de importación conserva sus resultados.

- [ ] **Step 5: Ejecutar Ruff y crear commit**

Run: `docker-compose exec api ruff check .`

```bash
git add backend/app/api/comparisons.py backend/app/api/router.py backend/tests/api/test_comparisons_api.py
git commit -m "feat: expose financial comparison endpoints"
```

---

### Task 5: Cliente TypeScript y reglas puras de selección

**Files:**
- Modify: `src/renderer/api.ts`
- Create: `src/renderer/comparison-state.ts`
- Test: `tests/unit/comparison-state.test.ts`

**Interfaces:**
- Consumes: contratos JSON del Task 4.
- Produces: `listComparisonStatements`, `createComparison`, `isChronologicallyBefore`, `formatComparisonValue`, `formatComparisonChange`.

- [ ] **Step 1: Escribir pruebas fallidas de estado y formato**

```typescript
import { describe, expect, it } from 'vitest';
import {
  formatComparisonChange,
  isChronologicallyBefore,
} from '../../src/renderer/comparison-state';

describe('comparison state', () => {
  it('orders balances by as-of date and results by interval', () => {
    expect(isChronologicallyBefore(balance('2024-12-31'), balance('2025-12-31'))).toBe(true);
    expect(isChronologicallyBefore(results('2025-01-01', '2025-03-31'), results('2024-01-01', '2024-12-31'))).toBe(false);
  });

  it('formats every non-numeric percentage state explicitly', () => {
    expect(formatComparisonChange(null, 'NEW')).toBe('Nueva');
    expect(formatComparisonChange(null, 'REMOVED')).toBe('Ya no presente');
    expect(formatComparisonChange(null, 'UNCHANGED')).toBe('Sin cambio');
    expect(formatComparisonChange(null, 'NO_BASE')).toBe('Sin base comparable');
    expect(formatComparisonChange(25, 'CALCULATED')).toBe('+25.0%');
  });
});
```

- [ ] **Step 2: Ejecutar y verificar el fallo de importación**

Run: `npm test -- tests/unit/comparison-state.test.ts`

Expected: FAIL porque `comparison-state.ts` no existe.

- [ ] **Step 3: Añadir tipos y llamadas API**

Agregar tipos alineados con Pydantic:

```typescript
export type ComparisonStatement = {
  period_id: number;
  statement_type: 'BALANCE_GENERAL' | 'ESTADO_RESULTADOS';
  label: string;
  as_of_date: string | null;
  period_start: string | null;
  period_end: string | null;
  duration_days: number | null;
};

export type ComparisonRow = {
  key: string;
  account_id: number | null;
  code: string | null;
  name: string;
  level: number;
  base_value: number | null;
  comparison_value: number | null;
  absolute_change: number | null;
  percentage_change: number | null;
  change_status: 'CALCULATED' | 'NEW' | 'REMOVED' | 'UNCHANGED' | 'NO_BASE';
  children: ComparisonRow[];
};

export type ComparisonRequest = {
  statement_type: 'BALANCE_GENERAL' | 'ESTADO_RESULTADOS';
  base_period_id: number;
  comparison_period_id: number;
};

export type ComparisonResult = {
  statement_type: 'BALANCE_GENERAL' | 'ESTADO_RESULTADOS';
  base_statement: ComparisonStatement;
  comparison_statement: ComparisonStatement;
  warnings: string[];
  groups: ComparisonRow[];
};

export function listComparisonStatements(companyId: number, statementType?: string) {
  const query = statementType ? `?statement_type=${encodeURIComponent(statementType)}` : '';
  return request<ComparisonStatement[]>(`/api/companies/${companyId}/comparison-statements${query}`);
}

export function createComparison(companyId: number, payload: ComparisonRequest) {
  return request<ComparisonResult>(`/api/companies/${companyId}/comparisons`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Implementar reglas puras y formato**

`isChronologicallyBefore` usará `as_of_date` para Balance y `[period_start, period_end]` para Resultados. `formatComparisonValue` usará `Intl.NumberFormat` con moneda de la empresa, preservará `null` como `—` y no realizará cálculo financiero.

- [ ] **Step 5: Ejecutar pruebas y compilación TypeScript**

Run: `npm test -- tests/unit/comparison-state.test.ts`

Run: `npm run build:renderer`

Expected: PASS y compilación sin errores de tipos.

- [ ] **Step 6: Crear commit**

```bash
git add src/renderer/api.ts src/renderer/comparison-state.ts tests/unit/comparison-state.test.ts
git commit -m "feat: add comparison client and display state"
```

---

### Task 6: Página de Comparaciones y componentes

**Files:**
- Modify: `src/renderer/comparison-state.ts`
- Create: `src/renderer/pages/ComparisonPage.tsx`
- Create: `src/renderer/components/comparisons/StatementTypeSelector.tsx`
- Create: `src/renderer/components/comparisons/FinancialPeriodSelector.tsx`
- Create: `src/renderer/components/comparisons/ComparisonWarnings.tsx`
- Create: `src/renderer/components/comparisons/ComparisonTable.tsx`
- Test: `tests/unit/comparison-page-state.test.ts`

**Interfaces:**
- Consumes: `Company`, `ensureCompany`, `listComparisonStatements`, `createComparison`, funciones de `comparison-state.ts`.
- Produces: `ComparisonPage({ company, onFiles })` y componentes presentacionales tipados.

- [ ] **Step 1: Extraer un controlador testeable para solicitudes obsoletas**

La página mantendrá `requestVersionRef`. Antes de cada consulta incrementará el valor y solo aplicará la respuesta si coincide:

```typescript
const requestVersionRef = useRef(0);

async function loadStatements(nextType: StatementType) {
  const requestVersion = ++requestVersionRef.current;
  setLoading(true);
  try {
    const items = await listComparisonStatements(apiCompanyId, nextType);
    if (requestVersion === requestVersionRef.current) setStatements(items);
  } finally {
    if (requestVersion === requestVersionRef.current) setLoading(false);
  }
}
```

- [ ] **Step 2: Escribir pruebas fallidas de estados de página**

```typescript
describe('comparison page state', () => {
  it('shows the empty-state action when fewer than two compatible statements exist', () => {
    expect(getComparisonAvailability([statement(1)])).toEqual({ canCompare: false, reason: 'INSUFFICIENT' });
  });

  it('invalidates an older request after the statement type changes', () => {
    const tracker = createRequestTracker();
    const first = tracker.begin();
    const second = tracker.begin();
    expect(tracker.isCurrent(first)).toBe(false);
    expect(tracker.isCurrent(second)).toBe(true);
  });
});
```

Definir `getComparisonAvailability` y `createRequestTracker` en `comparison-state.ts` para probar la conducta sin instalar una biblioteca de DOM.

- [ ] **Step 3: Ejecutar la prueba y comprobar el fallo**

Run: `npm test -- tests/unit/comparison-page-state.test.ts`

Expected: FAIL por funciones ausentes.

- [ ] **Step 4: Implementar selectores y advertencias**

Los selectores serán controlados, tendrán `<label>` visible, opciones provenientes exclusivamente de la API y deshabilitarán el mismo período en el control opuesto. `ComparisonWarnings` usará `role="status"` para advertencias no bloqueantes y `role="alert"` para errores.

- [ ] **Step 5: Implementar tabla jerárquica**

`ComparisonTable` mantendrá un `Set<string>` de grupos expandidos. Renderizará grupos y descendientes recursivamente, con botón accesible:

```tsx
<button
  type="button"
  className="comparison-expand"
  aria-expanded={expanded.has(row.key)}
  onClick={() => onToggle(row.key)}
>
  <span aria-hidden="true">{expanded.has(row.key) ? '▾' : '▸'}</span>
  {row.name}
</button>
```

Los valores y porcentajes se presentarán mediante las funciones de formato del Task 5.

- [ ] **Step 6: Implementar `ComparisonPage`**

Flujo:

1. Resolver la empresa API mediante `ensureCompany`.
2. Cargar estados del tipo seleccionado.
3. Limpiar selecciones y resultado al cambiar tipo.
4. Validar localmente selección completa y orden para retroalimentación inmediata.
5. Solicitar la comparación al backend.
6. Mostrar advertencias devueltas y tabla.
7. Mostrar estado vacío con botón `onFiles` cuando hay menos de dos estados.

No calcular variaciones ni agregados en la página.

- [ ] **Step 7: Ejecutar pruebas y build de renderer**

Run: `npm test -- tests/unit/comparison-state.test.ts tests/unit/comparison-page-state.test.ts`

Run: `npm run build:renderer`

Expected: PASS y sin errores TypeScript.

- [ ] **Step 8: Crear commit**

```bash
git add src/renderer/comparison-state.ts src/renderer/pages/ComparisonPage.tsx src/renderer/components/comparisons tests/unit/comparison-page-state.test.ts
git commit -m "feat: build manual comparison workspace"
```

---

### Task 7: Integración de navegación y diseño visual

**Files:**
- Modify: `src/renderer/components/ContextHeader.tsx`
- Modify: `src/renderer/main.tsx`
- Modify: `src/renderer/navigation.ts`
- Modify: `src/renderer/styles.css`
- Modify: `tests/unit/navigation.test.ts`

**Interfaces:**
- Consumes: `ComparisonPage`, ruta existente `/comparisons`.
- Produces: navegación completa y encabezado sin controles globales en Comparaciones.

- [ ] **Step 1: Escribir prueba fallida de política del encabezado**

Agregar una función pura en `navigation.ts`:

```typescript
export function showsGlobalContextControls(path: string): boolean {
  return path !== '/comparisons' && path !== '/files';
}
```

Primero escribir la prueba:

```typescript
it('oculta los controles globales en Comparaciones y Archivos', async () => {
  const { showsGlobalContextControls } = await import('../../src/renderer/navigation');
  expect(showsGlobalContextControls('/comparisons')).toBe(false);
  expect(showsGlobalContextControls('/files')).toBe(false);
  expect(showsGlobalContextControls('/dashboard')).toBe(true);
});
```

- [ ] **Step 2: Ejecutar y confirmar el fallo**

Run: `npm test -- tests/unit/navigation.test.ts`

Expected: FAIL porque la función no existe.

- [ ] **Step 3: Integrar la página y controles opcionales**

Agregar `showControls?: boolean` a `ContextHeaderProps` con valor predeterminado `true`. Renderizar `.context-controls` solo cuando sea verdadero.

En `main.tsx`:

```tsx
if (activePath === '/comparisons') {
  return <ComparisonPage company={company} onFiles={() => setActivePath('/files')} />;
}
```

Y pasar `showControls={showsGlobalContextControls(activePath)}` a `ContextHeader`.

- [ ] **Step 4: Añadir estilos aislados**

Usar clases con prefijo `comparison-` para controles, tarjeta, advertencias, tabla, filas de grupo, indentación, signos y estado vacío. Reutilizar los colores existentes `#0350A7`, `#2A61EE`, `#0DC7E0`, `#47D4E7`, `#183152`, fondos claros y bordes actuales.

La tabla tendrá:

- Encabezado `position: sticky`.
- Primera columna flexible y columnas numéricas alineadas a la derecha.
- Desplazamiento horizontal en ventanas estrechas.
- Indicador textual junto al color de variación.
- Foco visible en botones y selectores.

- [ ] **Step 5: Ejecutar pruebas y compilación completa**

Run: `npm test`

Run: `npm run build`

Expected: todos los tests de Vitest pasan y Vite/Electron compilan.

- [ ] **Step 6: Crear commit**

```bash
git add src/renderer/components/ContextHeader.tsx src/renderer/main.tsx src/renderer/navigation.ts src/renderer/styles.css tests/unit/navigation.test.ts
git commit -m "feat: integrate comparisons into company workspace"
```

---

### Task 8: Documentación y verificación integral

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: módulo completo de Tasks 1–7.
- Produces: instrucciones de uso y evidencia final de regresión.

- [ ] **Step 1: Documentar el flujo manual**

Agregar una sección breve al README:

```markdown
### Comparaciones

1. Inicia API y aplicación.
2. Entra a una empresa y abre **Comparaciones**.
3. Selecciona Balance General o Estado de Resultados.
4. Selecciona primero el período anterior y luego el posterior.
5. Pulsa **Comparar** para ver totales, cuentas desplegables y variaciones.

Solo aparecen estados aprobados con saldos guardados. Los períodos de distinta duración muestran una advertencia y no se ajustan automáticamente.
```

- [ ] **Step 2: Ejecutar migraciones existentes y suite backend**

Run: `docker-compose exec api alembic upgrade head`

Run: `docker-compose exec api pytest -q`

Run: `docker-compose exec api ruff check .`

Expected: migración al último `head`, todos los tests pasan y Ruff informa `All checks passed!`.

- [ ] **Step 3: Ejecutar suite frontend y compilación**

Run: `npm test`

Run: `npm run build`

Run: `git diff --check`

Expected: todos los tests pasan, renderer y Electron compilan, y no existen errores de espacios.

- [ ] **Step 4: Realizar prueba manual con datos reales existentes**

Con API y Electron iniciados:

1. Abrir Comercial XYZ → Comparaciones.
2. Confirmar que no aparecen estados sin aprobar.
3. Comparar dos estados del mismo tipo en orden cronológico.
4. Expandir al menos un grupo y comprobar que sus detalles no alteran el total mostrado.
5. Confirmar que Archivos sigue accesible y el flujo de importación abre su revisión.
6. Si solo existe un estado compatible, confirmar el estado vacío y el botón **Ir a Archivos**.

- [ ] **Step 5: Crear commit de documentación**

```bash
git add README.md
git commit -m "docs: document manual financial comparisons"
```

- [ ] **Step 6: Solicitar revisión final**

Usar `superpowers:requesting-code-review` para revisar el diff completo contra la especificación, prestando atención a aislamiento por empresa, orden temporal, doble conteo, nulos y regresiones del importador.
