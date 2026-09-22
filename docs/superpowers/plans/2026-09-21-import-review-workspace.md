# Import Review Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la revisión dentro del modal por un workspace de pantalla completa donde se puedan visualizar, corregir y validar hojas financieras antes de aprobar una importación.

**Architecture:** `Archivos` seguirá iniciando la selección sin período. FastAPI detectará el período y devolverá una revisión persistida; Electron/React abrirá una ruta temporal de revisión con panel de hojas, tabla de preview y panel de edición. La importación definitiva de saldos seguirá fuera de este plan: aprobar solo cambiará el estado a `APPROVED` después de resolver las filas bloqueantes y validar el período.

**Tech Stack:** React, TypeScript, Vite, Electron, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, pytest, Ruff y Vitest.

**Spec:** `docs/superpowers/specs/2026-09-21-import-review-workspace-design.md`

## Global Constraints

- `Archivos` no tendrá selector manual de período durante la carga.
- El período se detectará usando título de hoja, nombre de hoja, nombre de archivo y contenido, en ese orden.
- El período final será editable y validado dentro de la revisión.
- Las filas `UNKNOWN`, `NEW_ACCOUNT` y `ERROR` bloquearán la confirmación hasta resolverse o ignorarse explícitamente.
- Las sugerencias fuzzy nunca confirmarán una cuenta automáticamente.
- Se conservarán el archivo original, valores originales y trazabilidad de cada fila.
- El soporte inicial de archivos será `.xlsx` y `.xlsm`; `.xls` queda fuera de alcance.
- Aprobar una revisión no importará todavía saldos definitivos a `account_balances`.

## Review Focus

- Libro con un período diferente en cada hoja: debe mostrar conflicto y exigir elección; cubierto en Task 1.
- Libro sin encabezados tradicionales: debe mostrar filas y columnas originales en preview; cubierto en Task 2.
- Período no detectable: debe quedar vacío/no validado y bloquear aprobación; cubierto en Task 1.
- Fila con cuenta desconocida: debe poder mapearse a una cuenta existente o ignorarse; cubierto en Task 3.
- Importación con muchas columnas: la tabla debe desplazarse internamente sin desplazar toda la aplicación; cubierto en Task 4.

---

### Task 1: Detectar y persistir el período de importación

**Files:**
- Create: `backend/app/services/period_detection_service.py`
- Create: `backend/app/schemas/period_detection.py`
- Modify: `backend/app/models/financial_import.py`
- Create: `backend/alembic/versions/003_add_import_period_detection.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/schemas/import_api.py`
- Create: `backend/tests/services/test_period_detection_service.py`
- Create: `backend/tests/api/test_import_period_api.py`

**Interfaces:**
- `detect_period(file_name: str, sheets: list[SheetSnapshot]) -> PeriodDetection` returns `label`, `year`, `month`, `source`, `confidence` and `conflict`.
- `FinancialImport` stores `detected_period_label`, `detected_period_year`, `detected_period_month`, `period_source`, `period_validated` and `period_conflict`.
- `PATCH /api/imports/{id}/period` accepts `{ "label": "2025", "year": 2025, "month": null }` and marks the period validated.

- [ ] **Step 1: Write failing detection tests** for year in sheet name, year in title, year in file name, conflicting sheet years and no detectable year.
- [ ] **Step 2: Run `docker-compose exec api pytest tests/services/test_period_detection_service.py -q`** and verify the new tests fail because the detector and fields do not exist.
- [ ] **Step 3: Implement period detection and migration** with explicit source priority and conflict reporting; do not silently choose a value when sheet years disagree.
- [ ] **Step 4: Include detection in `analyze_import`** and expose it from `ImportResponse`.
- [ ] **Step 5: Add and test the period update endpoint**; reject approval when `period_validated` is false or `period_conflict` remains true.
- [ ] **Step 6: Run `docker-compose exec api pytest -q && docker-compose exec api ruff check .`** and expect all tests to pass with no Ruff errors.

### Task 2: Preview financial sheets with source traceability

**Files:**
- Modify: `backend/app/schemas/import_api.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/api/imports.py`
- Create: `backend/tests/api/test_import_preview.py`
- Modify: `src/renderer/api.ts`
- Create: `src/renderer/components/imports/PreviewTable.tsx`
- Create: `src/renderer/components/imports/SheetList.tsx`

**Interfaces:**
- `get_sheet_preview(import_job: FinancialImport, sheet_name: str, limit: int = 200) -> PreviewResponse` returns original values, source row numbers and extracted row metadata.
- `GET /api/imports/{id}/sheets/{sheet_name}/preview` returns `sheet_name`, `columns`, `rows`, `total_rows` and `truncated`.
- `PreviewTable` receives `rows`, `columns`, `selectedRowId` and `onSelectRow`.

- [ ] **Step 1: Write failing API tests** for a report-style workbook, preserving row numbers, empty cells, numeric values and truncation metadata.
- [ ] **Step 2: Implement the typed preview response** without modifying the stored workbook.
- [ ] **Step 3: Implement `SheetList` and `PreviewTable`** with internal horizontal/vertical scrolling and a selected-row callback.
- [ ] **Step 4: Run backend preview tests and `npm test && npm run build`**.

### Task 3: Editable row mapping and review actions

**Files:**
- Create: `backend/app/schemas/review_api.py`
- Modify: `backend/app/api/imports.py`
- Modify: `backend/app/services/excel_import_service.py`
- Create: `backend/tests/api/test_import_review_api.py`
- Create: `src/renderer/components/imports/RowReviewPanel.tsx`
- Modify: `src/renderer/api.ts`

**Interfaces:**
- `PATCH /api/imports/{id}/rows/{row_id}` accepts `{ "action": "match", "account_id": 12 }` or `{ "action": "ignore" }`.
- `GET /api/companies/{company_id}/accounts?query=` returns accounts belonging only to the active company.
- `RowReviewPanel` receives the selected row, account search results, `onMatch` and `onIgnore`.

- [ ] **Step 1: Write failing tests** for matching an existing company account, rejecting an account from another company, ignoring a row and recalculating review counts.
- [ ] **Step 2: Implement company-scoped account search** and the review mutation; preserve original code/name while updating only resolution fields.
- [ ] **Step 3: Implement the panel** with current suggestion, searchable account selector, explicit `Asignar cuenta` and `Ignorar fila` actions.
- [ ] **Step 4: Prevent approval** when unresolved blocking rows remain or the period is unvalidated.
- [ ] **Step 5: Run backend tests, Ruff, frontend tests and build**.

### Task 4: Full-screen review workspace

**Files:**
- Create: `src/renderer/pages/ImportReviewPage.tsx`
- Modify: `src/renderer/main.tsx`
- Modify: `src/renderer/components/imports/ImportWizard.tsx`
- Modify: `src/renderer/pages/FilesPage.tsx`
- Modify: `src/renderer/styles.css`
- Create: `tests/unit/import-review-state.test.ts`

**Interfaces:**
- `ImportReviewPage` receives `importId`, `company`, `onBack` and `onApproved`.
- Route state uses `/imports/:id/review` in the existing lightweight path state, without adding a permanent sidebar item.
- `ImportWizard` ends after upload/analyze and navigates to the full-screen review workspace.

- [ ] **Step 1: Write failing frontend state tests** for entering review, changing sheets, editing period, selecting a row and returning to `Archivos`.
- [ ] **Step 2: Build the full-screen layout** with collapsed navigation, top import context, left `SheetList`, center `PreviewTable`, right `RowReviewPanel` and bottom action bar.
- [ ] **Step 3: Remove the period selector from `FilesPage` and the initial upload step**; display the detected/edited period only in review.
- [ ] **Step 4: Connect save, period validation, row mapping, ignore and approve actions to the API.
- [ ] **Step 5: Run `npm test && npm run build && git diff --check`**.

### Task 5: Import history and regression verification

**Files:**
- Modify: `src/renderer/pages/FilesPage.tsx`
- Modify: `backend/app/api/imports.py`
- Create: `backend/tests/api/test_import_history.py`
- Create: `tests/unit/files-page-state.test.ts`
- Modify: `README.md`

**Interfaces:**
- `GET /api/companies/{company_id}/imports` returns file name, validated period, status, created time and review summary.
- `FilesPage` displays approved, pending and failed imports for the active company.

- [ ] **Step 1: Write failing API and frontend tests** for company-scoped history and status display.
- [ ] **Step 2: Implement history query and replace the empty-state-only Files page** while preserving `+ Importar datos`.
- [ ] **Step 3: Document the new workflow and Fedora commands** in `README.md`.
- [ ] **Step 4: Run the full verification set:** `docker-compose exec api pytest -q`, `docker-compose exec api ruff check .`, `npm test`, `npm run build`, and `git diff --check`.
