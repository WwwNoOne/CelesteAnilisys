import type { Company } from './app-state';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

type ApiCompany = { id: number; name: string };
type ApiPeriod = { id: number; label: string; year: number };
export type ImportResult = { id: number; file_name: string; status: string; total_rows: number; recognized_rows: number; review_rows: number; new_accounts: number; error_rows: number };
export type ImportSheet = { sheet_name: string; sheet_type: string; confidence: number; header_row: number | null };
export type ImportPreview = { sheet_name: string; rows: Array<Array<string | number | null>>; total_rows: number };
export type ImportIssue = { id: number; source_sheet: string; source_row: number; original_code: string | null; original_name: string | null; status: string; match_type: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Error del servidor (${response.status})`);
  }
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

export function getImportSheets(importId: number): Promise<{ sheets: ImportSheet[] }> {
  return request(`/api/imports/${importId}/sheets`);
}

export function getImportIssues(importId: number): Promise<{ rows: ImportIssue[]; total: number }> {
  return request(`/api/imports/${importId}/issues`);
}

export function getSheetPreview(importId: number, sheetName: string): Promise<ImportPreview> {
  return request<ImportPreview>(`/api/imports/${importId}/sheets/${encodeURIComponent(sheetName)}/preview`);
}

export function reviewImportRow(importId: number, rowId: number, action: 'ignore'): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}/rows/${rowId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
  });
}

export function approveImport(importId: number): Promise<ImportResult> {
  return request<ImportResult>(`/api/imports/${importId}/approve`, { method: 'POST' });
}

export function fileFromBase64(name: string, base64: string): File {
  const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
  return new File([bytes], name, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}
