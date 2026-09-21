# Module 1: Import Financial Statements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un flujo inicial para subir archivos XLS/XLSX, analizarlos sin importar datos automáticamente, detectar hojas y filas financieras, y llevar los resultados a una revisión humana.

**Architecture:** Electron alojará la interfaz React existente. Un backend FastAPI separado ejecutará el análisis de archivos y expondrá una API REST. La lógica se dividirá en dominio, servicios, importadores y persistencia para que la lectura de Excel no quede mezclada con la interfaz ni con las reglas contables.

**Tech Stack:** Electron, React, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Table, react-dropzone, Python, FastAPI, Pydantic, SQLAlchemy, Alembic, pandas, openpyxl, RapidFuzz, PostgreSQL, Docker Compose, pytest y Ruff.

**Spec:** `docs/requirements/module1-import-financial-statements.md`

## Global Constraints

- Aceptar inicialmente `.xlsx` y `.xlsm` en la interfaz; conservar el soporte de `.xls` únicamente como capacidad futura documentada porque `openpyxl` no procesa ese formato.
- No importar definitivamente al pulsar “Analizar archivo”.
- La revisión humana es obligatoria para filas `NEEDS_REVIEW`, `UNKNOWN`, `NEW_ACCOUNT` y `ERROR`; la ambigüedad se representará como `NEEDS_REVIEW` con un motivo `AMBIGUOUS`.
- Conservar siempre valores originales, normalizados y resueltos.
- Tratar los códigos contables como strings, nunca como integers.
- El código exacto tiene prioridad sobre nombre, alias y fuzzy matching.
- RapidFuzz solo produce sugerencias; nunca confirma una cuenta por sí solo.
- Separar la cuenta de sus saldos y de su archivo de origen.
- No añadir Redis, Celery, Polars ni DuckDB.
- No crear códigos contables arbitrarios automáticamente.
- Mantener el desarrollo reproducible con Docker Compose y pruebas automatizadas.

---

### Task 1: Backend reproducible y servicios locales

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/router.py`
- Create: `backend/tests/test_health.py`
- Create: `docker-compose.yml`
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Produces `GET /health` with `{ "status": "ok" }`.
- Produces a FastAPI application importable as `app.main:app`.
- Produces a PostgreSQL service reachable by the backend through environment variables.

- [ ] **Step 1: Write the failing health test**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint_returns_ok():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && pytest tests/test_health.py -q`

Expected: FAIL because `app.main` and `/health` do not exist.

- [ ] **Step 3: Implement the minimal FastAPI app and project dependencies**

Add FastAPI, Uvicorn, Pydantic settings, pytest and Ruff to `backend/pyproject.toml`. Register `/health` in `app/main.py` and keep database initialization out of this endpoint.

- [ ] **Step 4: Add Docker Compose for backend and PostgreSQL**

Define services `api` and `db`, expose API port `8000` and PostgreSQL port `5432`, and read credentials from `.env.example` without committing secrets.

- [ ] **Step 5: Run the test and static checks**

Run: `cd backend && pytest tests/test_health.py -q && ruff check .`

Expected: PASS with one test and no Ruff errors.

- [ ] **Step 6: Document local startup**

Document `docker compose up --build`, `pytest`, and `ruff check .` in `README.md`.

---

### Task 2: Dominio contable, normalización y estados

**Files:**
- Create: `backend/app/domain/enums.py`
- Create: `backend/app/domain/entities.py`
- Create: `backend/app/normalizers/text_normalizer.py`
- Create: `backend/tests/domain/test_text_normalizer.py`
- Create: `backend/tests/domain/test_account_identity.py`

**Interfaces:**
- `normalize_account_name(text: str) -> str` returns an uppercase, accent-free, whitespace-normalized string while preserving meaningful `&`, `-` and `/` characters.
- `AccountType` contains `ACTIVO`, `PASIVO`, `PATRIMONIO`, `INGRESO`, `COSTO`, `GASTO`, `OTRO`.
- `MatchType` contains `EXACT_CODE`, `CODE_AND_NAME`, `NORMALIZED_NAME`, `ALIAS`, `CONTEXT`, `FUZZY`, `NONE`.
- `RowStatus` contains `MATCHED`, `NEEDS_REVIEW`, `UNKNOWN`, `NEW_ACCOUNT`, `ERROR`, `IGNORED`.
- Account identity stores `code` as `str` and keeps `name` and `normalized_name` separately.

- [ ] **Step 1: Write failing normalization tests**

```python
def test_normalize_account_name_removes_accents_and_extra_spaces():
    assert normalize_account_name(" Gastos   de Administración ") == "GASTOS DE ADMINISTRACION"
    assert normalize_account_name("Vehículos") == "VEHICULOS"


def test_account_code_keeps_leading_zeroes():
    account = Account(code="01", name="Activo")
    assert account.code == "01"
```

- [ ] **Step 2: Run tests and verify the expected failure**

Run: `cd backend && pytest tests/domain/test_text_normalizer.py tests/domain/test_account_identity.py -q`

Expected: FAIL because the normalizer and entities do not exist.

- [ ] **Step 3: Implement the normalizer and domain enums/entities**

Use `unicodedata.normalize`, remove invisible control characters, collapse whitespace, and retain the raw name outside the normalizer. Do not normalize away meaningful punctuation.

- [ ] **Step 4: Run domain tests and Ruff**

Run: `cd backend && pytest tests/domain -q && ruff check .`

Expected: PASS.

---

### Task 3: Persistence model and migrations

**Files:**
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/models/company.py`
- Create: `backend/app/models/account.py`
- Create: `backend/app/models/account_alias.py`
- Create: `backend/app/models/account_balance.py`
- Create: `backend/app/models/financial_import.py`
- Create: `backend/app/models/import_row.py`
- Create: `backend/app/models/period.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_import_models.py`
- Create: `backend/tests/db/test_model_constraints.py`

**Interfaces:**
- `Account` stores `code`, `name`, `normalized_name`, `account_type`, `nature`, `level`, `parent_code` and `financial_statement`.
- `AccountAlias` stores normalized aliases linked to an account.
- `AccountBalance` links company, period, account and source import without duplicating accounts per year.
- `FinancialImport` stores `UPLOADED`, `ANALYZING`, `READY_FOR_REVIEW`, `APPROVED`, `IMPORTED` and `FAILED`.
- `ImportRow` stores source sheet, Excel row, raw code/name, normalized name, matched account, match type, confidence and status.

- [ ] **Step 1: Write failing model tests**

Test that two accounts with different string codes can share `normalized_name == "HONORARIOS"`, and that an account code such as `"01"` is persisted without losing its leading zero.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && pytest tests/db/test_model_constraints.py -q`

Expected: FAIL because SQLAlchemy models and database setup do not exist.

- [ ] **Step 3: Implement models, relationships and indexes**

Use unique constraints on account code within the relevant company/catalog context, not globally on normalized name. Add indexes for import id, status, normalized name and source sheet.

- [ ] **Step 4: Create and run the initial Alembic migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/db/test_model_constraints.py -q`

Expected: PASS.

---

### Task 4: Excel reader, sheet classification and header detection

**Files:**
- Create: `backend/app/importers/excel_reader.py`
- Create: `backend/app/importers/sheet_classifier.py`
- Create: `backend/app/importers/header_detector.py`
- Create: `backend/app/schemas/import_analysis.py`
- Create: `backend/tests/importers/test_sheet_classifier.py`
- Create: `backend/tests/importers/test_header_detector.py`
- Create: `backend/tests/fixtures/financial_sample.xlsx`

**Interfaces:**
- `read_workbook(path: Path) -> WorkbookSnapshot` reads workbook metadata and cell values without persisting accounts.
- `classify_sheet(name: str, rows: list[list[object]]) -> SheetTypeResult` returns `sheet_name`, normalized name, type and confidence.
- `detect_header(rows: list[list[object]]) -> HeaderDetection` returns row index, mapped candidate fields and confidence.
- `SheetType` contains `BALANCE_COMPROBACION`, `ESTADO_SITUACION_FINANCIERA`, `ESTADO_RESULTADOS`, `FLUJO_EFECTIVO`, `DESCONOCIDO`.

- [ ] **Step 1: Create fixture and failing tests**

Cover equivalent sheet names such as `Balance General`, `Estado de Resultados` and `Pérdidas y Ganancias`; include title rows and blank rows before headers.

- [ ] **Step 2: Run importer tests and verify failure**

Run: `cd backend && pytest tests/importers -q`

Expected: FAIL because reader, classifier and detector do not exist.

- [ ] **Step 3: Implement workbook reading**

Use pandas/openpyxl for `.xlsx` and `.xlsm`, preserve sheet order and keep source values unchanged. Reject unsupported extensions with a typed validation error.

- [ ] **Step 4: Implement sheet classification**

Normalize the sheet name, score known terms, inspect content when the name is insufficient, and return `DESCONOCIDO` with confidence instead of forcing a type.

- [ ] **Step 5: Implement header detection**

Inspect the first rows for normalized candidates including `CODIGO`, `CUENTA`, `SALDO`, `CARGOS`, `DEBE`, `ABONOS`, `HABER`, `SALDO ACTUAL` and `SALDO FINAL`. Return confidence and never assume row zero.

- [ ] **Step 6: Run importer tests**

Run: `cd backend && pytest tests/importers -q && ruff check .`

Expected: PASS.

---

### Task 5: Account extraction, matching and traceability

**Files:**
- Create: `backend/app/services/account_extraction_service.py`
- Create: `backend/app/services/account_matching_service.py`
- Create: `backend/app/matchers/account_matcher.py`
- Create: `backend/app/schemas/import_row.py`
- Create: `backend/tests/services/test_account_matching_service.py`

**Interfaces:**
- `extract_account_candidates(sheet: SheetSnapshot, header: HeaderDetection) -> list[AccountCandidate]` preserves source sheet and row number.
- `match_account(candidate: AccountCandidate, catalog: AccountCatalog) -> MatchResult` applies exact code, code plus normalized name, contextual name, alias, fuzzy suggestion and finally review.
- Fuzzy results always return `RowStatus.NEEDS_REVIEW` unless stronger evidence exists.

- [ ] **Step 1: Write failing matching tests**

Cover exact code, leading-zero codes, two `HONORARIOS` accounts with different codes, aliases, misspellings such as `Lobricantes`, and unknown accounts.

- [ ] **Step 2: Run matching tests and verify failure**

Run: `cd backend && pytest tests/services/test_account_matching_service.py -q`

Expected: FAIL because extraction and matching services do not exist.

- [ ] **Step 3: Implement candidate extraction**

Create candidates with `original_code`, `original_name`, `normalized_name`, `sheet`, `excel_row`, raw values and `is_group` when the row is a hierarchy/group row rather than a transactional account.

- [ ] **Step 4: Implement ordered matching**

Use code as string, consult context before fuzzy matching, return match type and confidence, and never create an account silently.

- [ ] **Step 5: Run tests and inspect results**

Run: `cd backend && pytest tests/services/test_account_matching_service.py -q`

Expected: PASS with ambiguous and fuzzy cases explicitly marked for review.

---

### Task 6: Import analysis API without commit

**Files:**
- Create: `backend/app/api/imports.py`
- Create: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/api/test_import_analysis.py`

**Interfaces:**
- `POST /api/imports` accepts company, period and `.xlsx`/`.xlsm` upload, stores the original file in a controlled temporary area and returns an import id.
- `POST /api/imports/{id}/analyze` runs sheet detection, header detection, extraction and matching, then sets status `READY_FOR_REVIEW`.
- `GET /api/imports/{id}` returns import status and summary.
- `GET /api/imports/{id}/sheets` returns detected sheets and types.
- `GET /api/imports/{id}/rows` returns traceable rows with pagination.
- `GET /api/imports/{id}/issues` returns only rows requiring review.

- [ ] **Step 1: Write failing API tests**

Test accepted extensions, rejected PDF, upload status `UPLOADED`, analysis status `READY_FOR_REVIEW`, detected sheets and preserved source row numbers.

- [ ] **Step 2: Run API tests and verify failure**

Run: `cd backend && pytest tests/api/test_import_analysis.py -q`

Expected: FAIL because routes and service do not exist.

- [ ] **Step 3: Implement upload and analysis orchestration**

Keep endpoints thin: validation and HTTP mapping in the route, orchestration in `ExcelImportService`, and reading/matching in dedicated components.

- [ ] **Step 4: Add safe error handling**

Set `FAILED` with an actionable message for unreadable workbooks, unsupported extensions and malformed rows; never partially commit accounts or balances during analysis.

- [ ] **Step 5: Run API and importer tests**

Run: `cd backend && pytest tests/api tests/importers tests/services -q`

Expected: PASS.

---

### Task 7: Electron/React import wizard and upload screen

**Files:**
- Create: `src/renderer/pages/imports/NewImportPage.tsx`
- Create: `src/renderer/pages/imports/AnalyzeImportPage.tsx`
- Create: `src/renderer/pages/imports/ReviewImportPage.tsx`
- Create: `src/renderer/components/imports/ExcelDropzone.tsx`
- Create: `src/renderer/components/imports/ImportSummary.tsx`
- Create: `src/renderer/lib/import-api.ts`
- Modify: `src/renderer/main.tsx`
- Modify: `src/renderer/styles.css`
- Modify: `package.json`
- Create: `tests/unit/import-api.test.ts`

**Interfaces:**
- Frontend route `/imports/new` renders `IMPORTAR ESTADOS FINANCIEROS` with company selector, period selector, dropzone, accepted-format hint and `Analizar archivo` button.
- `ExcelDropzone` accepts `.xlsx,.xlsm`, supports click and drag-and-drop, and exposes `onFileSelected(file: File)`.
- `analyzeImport(file: File, companyId: string, periodId: string) -> Promise<ImportAnalysis>` calls the FastAPI upload and analyze endpoints.
- The button changes to an analyzing state and navigates to `/imports/:id/analyze`; it never presents itself as an import/commit action.

- [ ] **Step 1: Write failing UI/API contract tests**

Test accepted extensions, rejected `.pdf`, required company/period fields and request construction for the upload endpoint.

- [ ] **Step 2: Run frontend tests and verify failure**

Run: `npm test -- tests/unit/import-api.test.ts`

Expected: FAIL because the import API client and screens do not exist.

- [ ] **Step 3: Add frontend dependencies and design tokens**

Add Tailwind CSS, shadcn/ui primitives, TanStack Table and react-dropzone only where the first module needs them. Keep the existing palette and use color only for success, warning, error and information states.

- [ ] **Step 4: Implement the upload screen**

Keep the screen legible and sparse: title, selectors, dropzone, selected-file state, validation messages and a single `Analizar archivo` action.

- [ ] **Step 5: Implement API client and analyze navigation**

Use the backend base URL from configuration, surface server errors, and preserve the returned import id for the next screens.

- [ ] **Step 6: Run frontend tests and build**

Run: `npm test -- tests/unit/import-api.test.ts && npm run build`

Expected: PASS and a successful renderer/Electron build.

---

### Task 8: Analysis and human review screens

**Files:**
- Create: `src/renderer/components/imports/SheetDetector.tsx`
- Create: `src/renderer/components/imports/ColumnMapper.tsx`
- Create: `src/renderer/components/imports/AccountReviewTable.tsx`
- Create: `src/renderer/components/imports/AccountMatchBadge.tsx`
- Create: `src/renderer/components/imports/ImportIssuesFilter.tsx`
- Create: `src/renderer/components/imports/NewAccountDialog.tsx`
- Create: `src/renderer/components/imports/FinancialValidationSummary.tsx`
- Modify: `src/renderer/pages/imports/AnalyzeImportPage.tsx`
- Modify: `src/renderer/pages/imports/ReviewImportPage.tsx`
- Create: `tests/unit/import-review.test.tsx`

**Interfaces:**
- Analysis screen shows file name, sheet count, each detected sheet, type and confidence, with `Atrás` and `Continuar`.
- Review table columns are status, Excel code, Excel account, system code, system account, type, match type, confidence and actions.
- Actions include selecting a suggestion, marking a new account, ignoring a row, editing assignment and confirming equivalence.
- Summary shows found rows, recognized accounts, new accounts, possible errors, ambiguous accounts and errors.
- Continue is disabled while unresolved review-required rows remain.

- [ ] **Step 1: Write failing component tests**

Test that fuzzy and ambiguous rows show review status, that issue filtering hides matched rows, and that the continue action is blocked until review-required rows are resolved.

- [ ] **Step 2: Run component tests and verify failure**

Run: `npm test -- tests/unit/import-review.test.tsx`

Expected: FAIL because the review components do not exist.

- [ ] **Step 3: Implement sheet analysis and configurable column mapping**

Show detected headers, allow the user to choose header row and map code/name/opening/debits/credits/ending columns, and preserve manual mapping in the import state.

- [ ] **Step 4: Implement the TanStack review table**

Add search, filters, sorting, “only problems” mode, match badges and explicit row actions. Never convert a fuzzy suggestion into a confirmed account without user action.

- [ ] **Step 5: Implement new-account dialog and issue resolution**

Require code/catalog context when creating a new account; if a valid code cannot be determined, keep the row in manual configuration rather than inventing a code.

- [ ] **Step 6: Run component tests and renderer build**

Run: `npm test -- tests/unit/import-review.test.tsx && npm run build`

Expected: PASS.

---

### Task 9: Approval, commit and financial validation foundation

**Files:**
- Create: `backend/app/services/financial_validation_service.py`
- Create: `backend/app/validators/financial_validator.py`
- Modify: `backend/app/api/imports.py`
- Create: `backend/tests/services/test_financial_validation_service.py`
- Create: `backend/tests/api/test_import_commit.py`

**Interfaces:**
- `FinancialValidationService.validate(import_id: UUID) -> list[ValidationResult]` returns expected value, actual value, difference and status without blocking small configurable differences.
- `POST /api/imports/{id}/approve` succeeds only after all review-required rows have explicit resolutions.
- `POST /api/imports/{id}/commit` writes balances and resolved rows, changes status to `IMPORTED`, and is never called by analysis.

- [ ] **Step 1: Write failing validation and commit tests**

Cover `ACTIVO = PASIVO + PATRIMONIO`, `INGRESOS - COSTOS - GASTOS = RESULTADO`, unresolved review rows blocking approval, and a successful transaction that preserves source references.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend && pytest tests/services/test_financial_validation_service.py tests/api/test_import_commit.py -q`

Expected: FAIL because approval, commit and validation services do not exist.

- [ ] **Step 3: Implement validation results and tolerance**

Keep validation advisory, store the difference and status, and make tolerance configurable through settings.

- [ ] **Step 4: Implement approval and transactional commit**

Require explicit review resolution, persist accounts/aliases/balances/import rows in one transaction, and retain raw values and source locations.

- [ ] **Step 5: Run the full test suites**

Run: `cd backend && pytest -q && ruff check .` and then from the repository root `npm test && npm run build`.

Expected: all tests pass and both backend and Electron builds succeed.

---

## Execution Order

Implement tasks in order. Tasks 1–3 establish the backend and domain foundation; tasks 4–6 make analysis independently usable; tasks 7–8 connect the existing Electron UI to the analysis flow; task 9 enables the controlled human-approved commit.

At the end of each task, run its listed test commands and create a focused commit containing only that task's files.

## Plan Self-Review

- Sheet classification, header detection, account normalization, matching, traceability, import states, review UI, manual mapping, aliases, validation and commit are each assigned to an explicit task.
- No task treats fuzzy matching as automatic confirmation.
- Account names and codes are stored separately, with code strings preserving leading zeroes.
- The original `modulo1.txt` is now preserved as `docs/requirements/module1-import-financial-statements.md`.
- The existing Electron frontend is extended rather than replaced.
- `.xls` is deliberately excluded from the initial upload contract because the selected `openpyxl` path supports `.xlsx` and `.xlsm`; adding `.xls` requires a separate reader choice and test fixture.
