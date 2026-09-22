# Independent Sheet Statements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Treat each valid workbook sheet as an independently dated, reviewed, validated, and approved financial statement while making every lateral account/balance block independently editable.

**Architecture:** `FinancialImport` remains the uploaded-file container and a new `ImportedStatement` record owns each sheet's lifecycle and temporal metadata. `ImportRow` candidates point to that statement and persist their source text/amount columns; preview responses group candidates under one physical Excel row. Sheet-ID-based endpoints enforce isolation and the React review workspace operates entirely on the selected statement.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL/SQLite tests, pytest, React, TypeScript, Vitest, Vite, Electron.

**Spec:** `docs/superpowers/specs/2026-09-22-independent-sheet-statements-design.md`

## Global Constraints

- One workbook sheet represents at most one financial statement.
- Invalid, empty, auxiliary, or multi-statement sheets are discarded with a visible reason.
- Period metadata and approval belong to the individual sheet, never to the workbook globally.
- Approved sheets are immutable.
- Each physical Excel row renders once; each `account + balance` block is independently selectable and editable.
- Approval remains blocked until temporal, mapping, canonical-role, duplicate, and mathematical validation pass.
- Existing global import fields remain temporarily for compatibility and are not authoritative for the new flow.

## Review Focus

- A workbook containing valid and auxiliary sheets must keep the valid statements and visibly discard only the auxiliary sheets; covered in Task 2.
- Two valid sheets with different periods must never share period metadata or balances; covered in Tasks 3 and 4.
- Two lateral account blocks on one row must remain separately addressable after preview refresh; covered in Tasks 2 and 5.
- Attempts to edit or reapprove an approved sheet must fail server-side; covered in Task 4.
- Legacy pending and approved imports must migrate without losing row or balance provenance; covered in Task 1.

---

### Task 1: Persist the per-sheet statement aggregate

**Files:**
- Create: `backend/app/models/imported_statement.py`
- Create: `backend/alembic/versions/010_add_imported_statements.py`
- Modify: `backend/app/domain/enums.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/financial_import.py`
- Modify: `backend/app/models/import_row.py`
- Modify: `backend/app/models/account_balance.py`
- Test: `backend/tests/db/test_imported_statement_models.py`

**Interfaces:**
- Produces: `ImportedStatement`, `StatementImportStatus`, `ImportRow.imported_statement_id`, `source_text_column`, `source_amount_column`, and `AccountBalance.imported_statement_id`.
- Consumes: existing `FinancialImport`, `Period`, `ImportRow`, and `AccountBalance` relationships.

- [ ] **Step 1: Write failing model tests**

Create tests which persist two statements for one import, attach two same-row candidates with different column coordinates, enforce unique `(source_import_id, sheet_name)`, and prove an approved statement can retain its period and balance provenance.

```python
left = ImportRow(source_import_id=job.id, imported_statement_id=statement.id,
                 source_sheet="2024", source_row=8,
                 source_text_column=0, source_amount_column=1,
                 original_name="EFECTIVO", ending_balance=Decimal("100"))
right = ImportRow(source_import_id=job.id, imported_statement_id=statement.id,
                  source_sheet="2024", source_row=8,
                  source_text_column=4, source_amount_column=5,
                  original_name="CUENTAS POR PAGAR", ending_balance=Decimal("75"))
assert {(row.source_text_column, row.source_amount_column) for row in (left, right)} == {(0, 1), (4, 5)}
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `docker-compose exec api pytest -q tests/db/test_imported_statement_models.py`

Expected: FAIL because `ImportedStatement` and the new columns do not exist.

- [ ] **Step 3: Add the enum, model, relationships, and migration**

Define:

```python
class ImportStatus(StrEnum):
    # existing values remain
    DISCARDED = "DISCARDED"

class StatementImportStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    DISCARDED = "DISCARDED"
```

`ImportedStatement` stores source order/name, detected type/confidence, discard reason, period metadata, counters, status, and approval timestamp. Migration `010_imported_statements` makes `financial_imports.period_id` nullable, creates statement rows for existing distinct source sheets, backfills row links and approved state from `approved_sheets`, and adds source-column and balance-provenance columns.

- [ ] **Step 4: Run model and constraint tests**

Run: `docker-compose exec api pytest -q tests/db/test_imported_statement_models.py tests/db/test_model_constraints.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/app backend/alembic/versions/010_add_imported_statements.py backend/tests/db
git commit -m "feat: persist imported statements per sheet"
```

### Task 2: Analyze sheets independently and preserve block coordinates

**Files:**
- Create: `backend/app/services/sheet_statement_service.py`
- Modify: `backend/app/services/account_extraction_service.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/services/period_detection_service.py`
- Test: `backend/tests/services/test_sheet_statement_service.py`
- Test: `backend/tests/services/test_account_matching_service.py`
- Test: `backend/tests/integration/test_real_workbook_accounting_flow.py`

**Interfaces:**
- Consumes: Task 1's `ImportedStatement` and source-column fields.
- Produces: `analyze_sheet(sheet, file_name) -> SheetAnalysisDecision` and persisted statement/candidate records used by Task 3.

- [ ] **Step 1: Write failing sheet-analysis tests**

Cover a valid report plus auxiliary sheet, no valid sheets, two valid sheets with different detected dates, multiple state types in one sheet, and two lateral blocks:

```python
decision = analyze_sheet(valid_sheet, "empresa.xlsx")
assert decision.valid is True
assert [(c.text_column, c.amount_column) for c in decision.candidates] == [(0, 1), (4, 5)]

discarded = analyze_sheet(auxiliary_sheet, "empresa.xlsx")
assert discarded.valid is False
assert discarded.discard_reason
```

- [ ] **Step 2: Run focused service tests and verify RED**

Run: `docker-compose exec api pytest -q tests/services/test_sheet_statement_service.py tests/services/test_account_matching_service.py`

Expected: FAIL because sheet decisions and candidate coordinates are missing.

- [ ] **Step 3: Implement independent analysis**

Add `text_column` and `amount_column` to `AccountCandidate`; populate them from both header blocks and `RowBlock`. `analyze_import` must create one `ImportedStatement` per physical sheet, discard invalid/multi-statement sheets with reasons, detect time data from that sheet, and add candidates only for valid sheets.

The valid-sheet predicate requires a recognized financial statement type and at least one account candidate with a numeric balance. A workbook with zero valid sheets reaches the aggregate discarded/failed-with-reason state without periods or balances.

- [ ] **Step 4: Run service and real-workbook tests**

Run: `docker-compose exec api pytest -q tests/services/test_sheet_statement_service.py tests/services/test_account_matching_service.py tests/integration/test_real_workbook_accounting_flow.py`

Expected: PASS and real example sheets receive independent dates.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/app/services backend/tests/services backend/tests/integration
git commit -m "feat: analyze workbook sheets independently"
```

### Task 3: Expose statement-scoped review and grouped preview APIs

**Files:**
- Modify: `backend/app/schemas/import_api.py`
- Modify: `backend/app/api/imports.py`
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/services/accounting_validation_service.py`
- Test: `backend/tests/api/test_import_preview.py`
- Test: `backend/tests/api/test_import_statement_workflow.py`

**Interfaces:**
- Consumes: `ImportedStatement` and candidates from Tasks 1-2.
- Produces: statement-ID routes and `SheetPreviewRow.candidates: list[SheetPreviewCandidate]`.

- [ ] **Step 1: Write failing API tests**

Verify list responses include valid/discarded status and reasons; period updates affect one statement; preview emits one physical row with two candidates; validation is isolated by statement; and counters count candidates rather than visual rows.

```python
row = response.json()["row_details"][7]
assert len(row["candidates"]) == 2
assert row["candidates"][0]["text_column"] == 0
assert row["candidates"][1]["text_column"] == 4
assert len(response.json()["rows"]) == response.json()["total_rows"]
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `docker-compose exec api pytest -q tests/api/test_import_preview.py tests/api/test_import_statement_workflow.py`

Expected: FAIL because responses are row-oriented and period updates are import-wide.

- [ ] **Step 3: Implement statement-ID APIs and grouped preview**

Add schemas:

```python
class SheetPreviewCandidate(BaseModel):
    import_row_id: int
    status: str
    account_code: str | None
    account_name: str | None
    row_classification: str
    canonical_role: CanonicalRole | None
    ending_balance: Decimal | None
    text_column: int
    amount_column: int | None

class SheetPreviewRow(BaseModel):
    source_row: int
    cells: list[Any]
    candidates: list[SheetPreviewCandidate]
```

Add statement-scoped list, preview, period update, validation and row-review behavior. Keep old name-based read routes only as compatibility adapters. Reject mutation when `statement.status == APPROVED`.

- [ ] **Step 4: Run all import API tests**

Run: `docker-compose exec api pytest -q tests/api`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add backend/app/api backend/app/schemas backend/app/services backend/tests/api
git commit -m "feat: add statement scoped review APIs"
```

### Task 4: Approve, validate, and replace one sheet atomically

**Files:**
- Modify: `backend/app/services/excel_import_service.py`
- Modify: `backend/app/services/accounting_validation_service.py`
- Modify: `backend/app/services/statement_duplicate_service.py`
- Modify: `backend/app/api/imports.py`
- Test: `backend/tests/api/test_import_statement_approval.py`
- Test: `backend/tests/services/test_accounting_validation_service.py`
- Test: `backend/tests/services/test_statement_duplicate_service.py`

**Interfaces:**
- Consumes: statement metadata and routes from Tasks 1-3.
- Produces: `approve_statement(db, statement, payload)` and aggregate import-status refresh.

- [ ] **Step 1: Write failing approval-isolation tests**

Test that approving statement A creates only A's period/balances, leaves B pending, blocks further edits to A, scopes duplicate replacement to A, and marks the file approved only after every valid statement is approved and all others discarded.

- [ ] **Step 2: Run approval tests and verify RED**

Run: `docker-compose exec api pytest -q tests/api/test_import_statement_approval.py tests/services/test_accounting_validation_service.py tests/services/test_statement_duplicate_service.py`

Expected: FAIL because approval still relies partly on the whole import.

- [ ] **Step 3: Implement atomic per-statement approval**

Within one transaction: reload and lock the statement, reject non-pending status, validate its dates/candidates/canonical equations, check duplicate key, resolve its period, write only its balances with statement provenance, mark approved, and derive the parent import status. Do not commit inside helper stages; commit once after all mutations succeed.

- [ ] **Step 4: Run approval and accounting suites**

Run: `docker-compose exec api pytest -q tests/api/test_import_statement_approval.py tests/services/test_accounting_validation_service.py tests/services/test_statement_duplicate_service.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add backend/app backend/tests/api/test_import_statement_approval.py backend/tests/services
git commit -m "feat: approve financial statements independently"
```

### Task 5: Build the sheet-scoped review workspace and cell-level selection

**Files:**
- Modify: `src/renderer/api.ts`
- Modify: `src/renderer/import-review-state.ts`
- Modify: `src/renderer/pages/ImportReviewPage.tsx`
- Modify: `src/renderer/components/imports/PreviewTable.tsx`
- Modify: `src/renderer/components/imports/RowReviewPanel.tsx`
- Modify: `src/renderer/styles.css`
- Test: `tests/unit/import-review-state.test.ts`
- Create: `tests/unit/import-preview-selection.test.tsx`

**Interfaces:**
- Consumes: Task 3's statement and grouped-candidate response contracts.
- Produces: selected candidate state, sheet-local period editor, `Aprobar hoja`, and immutable/discarded states.

- [ ] **Step 1: Write failing frontend state and component tests**

Pin candidate flattening and cell lookup:

```typescript
expect(countPendingCandidates(rows)).toBe(5);
expect(candidateAtColumn(row, 0)?.import_row_id).toBe(101);
expect(candidateAtColumn(row, 1)?.import_row_id).toBe(101);
expect(candidateAtColumn(row, 4)?.import_row_id).toBe(102);
expect(candidateAtColumn(row, 5)?.import_row_id).toBe(102);
```

Render a row with two candidates, click the left balance and right account independently, and assert only the chosen pair receives `financial-block-selected`.

- [ ] **Step 2: Run frontend tests and verify RED**

Run: `npm test -- tests/unit/import-review-state.test.ts tests/unit/import-preview-selection.test.tsx`

Expected: FAIL because preview details represent one entire selected row.

- [ ] **Step 3: Implement grouped candidate types and helpers**

Replace row-level candidate fields with `candidates`. Add pure helpers `candidateAtColumn`, `countPendingCandidates`, and `candidateIsPending`. Use candidate IDs as selection identity so preview refreshes preserve the correct lateral block.

- [ ] **Step 4: Implement the statement workspace UI**

Render every raw row once. Attach click handlers only to the candidate's text and amount cells; apply selected/invalid classes only to those cells. Move temporal fields into the selected-sheet header, show discarded reasons, lock approved sheets, and replace global approval with `Aprobar hoja`. Update the empty panel copy from “fila” to “cuenta y saldo”.

- [ ] **Step 5: Run frontend unit tests**

Run: `npm test`

Expected: all Vitest files PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add src/renderer tests/unit
git commit -m "feat: review sheet accounts as independent blocks"
```

### Task 6: Verify migrations, real workbooks, and packaged application

**Files:**
- Test: all backend and frontend suites

**Interfaces:**
- Consumes: complete implementation.
- Produces: migration and release evidence for the feature branch.

- [ ] **Step 1: Rebuild disposable services and apply migrations**

Run: `docker-compose down -v && docker-compose up --build -d --force-recreate`

Expected: database becomes healthy, API starts, and Alembic upgrades through revision 010.

- [ ] **Step 2: Run backend verification**

Run: `docker-compose exec api pytest -q && docker-compose exec api ruff check .`

Expected: all tests PASS and Ruff reports no errors.

- [ ] **Step 3: Run frontend and packaging verification**

Run: `npm test && npm run build`

Expected: all tests PASS and Vite/Electron build completes.

- [ ] **Step 4: Exercise real workbook analysis**

Run the integration tests against `data/examples`, confirming each accepted sheet has one statement record, its own dates, and no duplicated visual row for lateral blocks.

Run: `docker-compose exec api pytest -q tests/importers/test_real_workbooks.py tests/integration/test_real_workbook_accounting_flow.py`

Expected: PASS.

- [ ] **Step 5: Commit any verification-only corrections**

```bash
git add backend src tests docs
git commit -m "test: verify independent sheet statement workflow"
```
