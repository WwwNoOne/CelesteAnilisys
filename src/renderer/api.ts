import type { Company } from './app-state';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

type ApiCompany = { id: number; name: string };
type ApiPeriod = { id: number; label: string; year: number };
export type ImportResult = {
  id: number;
  company_id: number;
  file_name: string;
  status: string;
  total_rows: number;
  recognized_rows: number;
  review_rows: number;
  unknown_rows: number;
  new_accounts: number;
  error_rows: number;
  detected_period_label: string | null;
  detected_period_year: number | null;
  detected_period_month: number | null;
  period_source: string | null;
  period_validated: boolean;
  period_conflict: boolean;
  detected_statement_type?: string | null;
  detected_as_of_date?: string | null;
  detected_period_start?: string | null;
  detected_period_end?: string | null;
  detected_timeframe?: string | null;
};
export type ImportSheet = {
  sheet_name: string;
  sheet_type: string;
  confidence: number;
  header_row: number | null;
  status: string;
  discard_reason: string | null;
  as_of_date?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  timeframe?: string | null;
  date_label?: string | null;
  total_rows: number;
  recognized_rows: number;
  review_rows: number;
  unknown_rows: number;
  error_rows: number;
};
export type SheetPreviewRow = {
  source_row: number;
  cells: Array<string | number | null>;
  import_row_id: number | null;
  status: string | null;
  account_code: string | null;
  account_name: string | null;
  row_classification: string;
  canonical_role: CanonicalRole | null;
  ending_balance: string | null;
  source_text_column: number | null;
  source_amount_column: number | null;
  is_generated: boolean;
};

export type CanonicalRole = 'ACTIVO' | 'PASIVO' | 'PATRIMONIO'
  | 'VENTAS' | 'COSTO_VENTAS' | 'UTILIDAD_BRUTA'
  | 'GASTOS' | 'IMPUESTOS' | 'RESULTADO_EJERCICIO';

export type AccountingValidationStatus =
  | 'VALID'
  | 'MISMATCH'
  | 'MISSING_COMPONENTS'
  | 'DUPLICATE_CONFLICT';

export type AccountingRuleResult = {
  rule_id: string;
  label: string;
  status: AccountingValidationStatus;
  left_value: string | null;
  right_value: string | null;
  difference: string | null;
  tolerance: string;
  missing_roles: CanonicalRole[];
  row_ids: number[];
};

export type AccountingValidationResponse = {
  valid: boolean;
  rules: AccountingRuleResult[];
};

export type RowReviewPayload = {
  action: 'match' | 'ignore' | 'classify' | 'update_financial_line';
  account_id?: number;
  row_classification?: string;
  canonical_role?: CanonicalRole;
  ending_balance?: string;
};

export type ImportPreview = {
  sheet_name: string;
  columns: string[];
  rows: Array<Array<string | number | null>>;
  total_rows: number;
  truncated: boolean;
  row_details: SheetPreviewRow[];
  as_of_date?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  timeframe?: string | null;
  date_label?: string | null;
};
export type ImportIssue = { id: number; source_sheet: string; source_row: number; original_code: string | null; original_name: string | null; status: string; match_type: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Error del servidor (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function ensureCompany(company: Company): Promise<ApiCompany> {
  const existing = await request<ApiCompany[]>('/api/companies');
  return existing.find((item) => item.name === company.name) ?? request<ApiCompany>('/api/companies', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: company.name }),
  });
}

export async function ensurePeriod(companyId: number, label: string): Promise<ApiPeriod> {
  const periods = await request<ApiPeriod[]>(`/api/companies/${companyId}/periods`);
  const year = Number.parseInt(label, 10) || new Date().getFullYear();
  return periods.find((item) => item.label === label || item.year === year) ?? request<ApiPeriod>(`/api/companies/${companyId}/periods`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label: String(year), year }),
  });
}

export async function uploadImport(companyId: number, periodId: number, file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append('company_id', String(companyId)); form.append('period_id', String(periodId)); form.append('file', file);
  return request<ImportResult>('/api/imports', { method: 'POST', body: form });
}

export function analyzeImport(importId: number): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}/analyze`, { method: 'POST' });
}

export function getImport(importId: number): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}`);
}

export function getImportSheets(importId: number): Promise<{ sheets: ImportSheet[] }> {
  return request(`/api/imports/${importId}/sheets`);
}

export function getImportIssues(importId: number): Promise<{ rows: ImportIssue[]; total: number }> {
  return request(`/api/imports/${importId}/issues`);
}

export function getAccountingValidation(importId: number, sheetName?: string) {
  const qs = sheetName ? `?sheet_name=${encodeURIComponent(sheetName)}` : '';
  return request<AccountingValidationResponse>(`/api/imports/${importId}/accounting-validation${qs}`);
}

export function getSheetPreview(importId: number, sheetName: string, limit = 200): Promise<ImportPreview> {
  return request<ImportPreview>(`/api/imports/${importId}/sheets/${encodeURIComponent(sheetName)}/preview?limit=${limit}`);
}

export type ApiAccount = {
  id: number;
  company_id: number;
  code: string;
  name: string;
  normalized_name: string;
  account_type: string | null;
  statement: string;
  statement_label: string;
  category: string;
  hierarchy_path: string;
};

export function searchCompanyAccounts(
  companyId: number,
  query = '',
  statement?: string,
  category?: string,
): Promise<ApiAccount[]> {
  const params = new URLSearchParams();
  if (query) params.set('query', query);
  if (statement && statement !== 'ALL') params.set('statement', statement);
  if (category && category !== 'ALL') params.set('category', category);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<ApiAccount[]>(`/api/companies/${companyId}/accounts${qs}`);
}

export function createCompanyAccount(
  companyId: number,
  name: string,
  accountType = 'ACTIVO',
  statement?: string,
  category?: string,
  code?: string,
  canonicalRole?: CanonicalRole,
): Promise<ApiAccount> {
  return request<ApiAccount>(`/api/companies/${companyId}/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      code,
      account_type: accountType,
      statement,
      category,
      canonical_role: canonicalRole,
    }),
  });
}

export function reviewImportRow(
  importId: number,
  rowId: number,
  payload: RowReviewPayload,
): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}/rows/${rowId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function approveImport(importId: number): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}/approve`, { method: 'POST' });
}

export type SheetApprovalResult = {
  success: boolean;
  sheet_name: string;
  status: string;
  balances_saved: number;
  is_duplicate: boolean;
  duplicate_warning: string | null;
  period_id: number | null;
};

export function approveImportSheet(
  importId: number,
  sheetName: string,
  payload: {
    label?: string;
    year?: number;
    statement_type?: string;
    as_of_date?: string;
    period_start?: string;
    period_end?: string;
    timeframe?: string;
    overwrite?: boolean;
  } = {},
): Promise<SheetApprovalResult> {
  return request<SheetApprovalResult>(
    `/api/imports/${importId}/sheets/${encodeURIComponent(sheetName)}/approve`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
}

export function updateImportPeriod(
  importId: number,
  label: string,
  year: number,
  month: number | null = null,
  statementType?: string | null,
  asOfDate?: string | null,
  periodStart?: string | null,
  periodEnd?: string | null,
  timeframe?: string | null,
): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}/period`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      label,
      year,
      month,
      statement_type: statementType,
      as_of_date: asOfDate,
      period_start: periodStart,
      period_end: periodEnd,
      timeframe,
    }),
  });
}

export function listCompanyImports(companyId: number): Promise<ImportResult[]> {
  return request<ImportResult[]>(`/api/companies/${companyId}/imports`);
}

export function deleteImport(importId: number): Promise<void> {
  return request<void>(`/api/imports/${importId}`, { method: 'DELETE' });
}

export type ComparisonStatementType = 'BALANCE_GENERAL' | 'ESTADO_RESULTADOS';

export type ComparisonStatement = {
  period_id: number;
  statement_type: ComparisonStatementType;
  label: string;
  as_of_date: string | null;
  period_start: string | null;
  period_end: string | null;
  duration_days: number | null;
};

export type ComparisonChangeStatus =
  | 'CALCULATED'
  | 'NEW'
  | 'REMOVED'
  | 'UNCHANGED'
  | 'NO_BASE';

export type ComparisonSource = {
  import_id: number;
  sheet_name: string;
  source_row: number;
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
  change_status: ComparisonChangeStatus;
  base_source: ComparisonSource | null;
  comparison_source: ComparisonSource | null;
  children: ComparisonRow[];
  is_group?: boolean;
};

export type ComparisonRequest = {
  statement_type: ComparisonStatementType;
  base_period_id: number;
  comparison_period_id: number;
};

export type ComparisonResult = {
  statement_type: ComparisonStatementType;
  base_statement: ComparisonStatement;
  comparison_statement: ComparisonStatement;
  warnings: string[];
  groups: ComparisonRow[];
};

export function listComparisonStatements(
  companyId: number,
  statementType?: ComparisonStatementType,
): Promise<ComparisonStatement[]> {
  const query = statementType
    ? `?statement_type=${encodeURIComponent(statementType)}`
    : '';
  return request<ComparisonStatement[]>(
    `/api/companies/${companyId}/comparison-statements${query}`,
  );
}

export function createComparison(
  companyId: number,
  payload: ComparisonRequest,
): Promise<ComparisonResult> {
  return request<ComparisonResult>(`/api/companies/${companyId}/comparisons`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function fileFromBase64(name: string, base64: string): File {
  const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
  return new File([bytes], name, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}
