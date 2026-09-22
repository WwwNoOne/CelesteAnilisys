import { useEffect, useRef, useState } from 'react';
import {
  approveImport,
  approveImportSheet,
  getAccountingValidation,
  getSheetPreview,
  getImportSheets,
  reviewImportRow,
  updateImportPeriod,
  type AccountingValidationResponse,
  type ImportPreview,
  type ImportResult,
  type ImportSheet,
  type SheetPreviewRow,
} from '../api';
import type { Company } from '../app-state';
import {
  collectInvalidRowIds,
  createRequestTracker,
  isPendingPreviewRow,
} from '../import-review-state';
import { AccountingValidationPanel } from '../components/imports/AccountingValidationPanel';
import { PreviewTable } from '../components/imports/PreviewTable';
import { RowReviewPanel } from '../components/imports/RowReviewPanel';

type ImportReviewPageProps = {
  importId: number;
  company: Company;
  sheetName: string;
  onBack: () => void;
  onApproved: () => void;
};

export function ImportReviewPage({
  importId,
  company,
  sheetName,
  onBack,
  onApproved,
}: ImportReviewPageProps) {
  const [importJob, setImportJob] = useState<ImportResult | null>(null);
  const [sheets, setSheets] = useState<ImportSheet[]>([]);
  const selectedSheet = sheetName;
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [selectedRow, setSelectedRow] = useState<SheetPreviewRow | null>(null);
  const [periodInput, setPeriodInput] = useState<string>('');
  const [asOfDate, setAsOfDate] = useState<string>('');
  const [periodStart, setPeriodStart] = useState<string>('');
  const [periodEnd, setPeriodEnd] = useState<string>('');
  const [timeframe, setTimeframe] = useState<string>('ANNUAL');
  const [loading, setLoading] = useState(true);
  const [validatingPeriod, setValidatingPeriod] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approvingSheet, setApprovingSheet] = useState(false);
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [accountingValidation, setAccountingValidation] =
    useState<AccountingValidationResponse | null>(null);
  const validationTracker = useRef(createRequestTracker()).current;

  async function refreshAccountingValidation() {
    const requestId = validationTracker.begin();
    const validation = await getAccountingValidation(importId, sheetName);
    if (validationTracker.isCurrent(requestId)) {
      setAccountingValidation(validation);
    }
    return validation;
  }

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError('');
      try {
        const [sheetsData, previewInitial] = await Promise.all([
          getImportSheets(importId),
          // We will fetch initial job details from api
          fetch(`http://localhost:8000/api/imports/${importId}`).then((r) => r.json()) as Promise<ImportResult>,
        ]);
        setImportJob(previewInitial);
        setPeriodInput(previewInitial.detected_period_label ?? '');
        setSheets(sheetsData.sheets);

        if (sheetName) {
          const previewData = await getSheetPreview(importId, sheetName);
          setPreview(previewData);
          if (previewData.as_of_date) setAsOfDate(previewData.as_of_date);
          if (previewData.period_start) setPeriodStart(previewData.period_start);
          if (previewData.period_end) setPeriodEnd(previewData.period_end);
          if (previewData.timeframe) setTimeframe(previewData.timeframe);
          await refreshAccountingValidation();
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Error al cargar la importación');
      } finally {
        setLoading(false);
      }
    }
    void init();
  }, [importId]);

  async function handleValidatePeriod() {
    if (!importJob) return;
    const currentSheet = sheets.find((s) => s.sheet_name === selectedSheet);
    const stmtType = currentSheet?.sheet_type ?? 'ESTADO_RESULTADOS';
    const yearNum = Number.parseInt(periodInput.trim(), 10) || (asOfDate ? Number.parseInt(asOfDate.slice(0, 4), 10) : new Date().getFullYear());
    setValidatingPeriod(true);
    setError('');
    try {
      const updated = await updateImportPeriod(
        importId,
        periodInput.trim() || String(yearNum),
        yearNum,
        null,
        stmtType,
        asOfDate || undefined,
        periodStart || undefined,
        periodEnd || undefined,
        timeframe || undefined,
      );
      setImportJob(updated);
      setSuccessMessage('Metadatos temporales validados correctamente.');
      setTimeout(() => setSuccessMessage(''), 4000);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Error al validar las fechas');
    } finally {
      setValidatingPeriod(false);
    }
  }

  async function handleMatch(rowId: number, accountId: number) {
    setError('');
    const updatedJob = await reviewImportRow(importId, rowId, {
      action: 'match',
      account_id: accountId,
    });
    setImportJob(updatedJob);
    // Reload preview to show updated row badge
    if (selectedSheet) {
      const updatedPreview = await getSheetPreview(importId, selectedSheet);
      setPreview(updatedPreview);
      const updatedRowDetail = updatedPreview.row_details.find((r) => r.import_row_id === rowId);
      if (updatedRowDetail) {
        setSelectedRow(updatedRowDetail);
      }
    }
    await refreshAccountingValidation();
  }

  async function handleIgnore(rowId: number) {
    setError('');
    const updatedJob = await reviewImportRow(importId, rowId, { action: 'ignore' });
    setImportJob(updatedJob);
    if (selectedSheet) {
      const updatedPreview = await getSheetPreview(importId, selectedSheet);
      setPreview(updatedPreview);
      const updatedRowDetail = updatedPreview.row_details.find((r) => r.import_row_id === rowId);
      if (updatedRowDetail) {
        setSelectedRow(updatedRowDetail);
      }
    }
    await refreshAccountingValidation();
  }

  async function handleClassify(rowId: number, classification: string) {
    setError('');
    const updatedJob = await reviewImportRow(importId, rowId, {
      action: 'classify',
      row_classification: classification,
    });
    setImportJob(updatedJob);
    if (selectedSheet) {
      const updatedPreview = await getSheetPreview(importId, selectedSheet);
      setPreview(updatedPreview);
      const updatedRowDetail = updatedPreview.row_details.find((r) => r.import_row_id === rowId);
      if (updatedRowDetail) {
        setSelectedRow(updatedRowDetail);
      }
    }
    await refreshAccountingValidation();
  }

  async function handleUpdateFinancialLine(
    rowId: number,
    payload: Parameters<typeof reviewImportRow>[2],
  ) {
    setError('');
    const updatedJob = await reviewImportRow(importId, rowId, payload);
    setImportJob(updatedJob);
    if (selectedSheet) {
      const updatedPreview = await getSheetPreview(importId, selectedSheet);
      setPreview(updatedPreview);
      setSelectedRow(
        updatedPreview.row_details.find((row) => row.import_row_id === rowId) ?? null,
      );
      await refreshAccountingValidation();
    }
  }

  async function handleApproveSheet(overwrite = false) {
    if (!importJob || !selectedSheet) return;
    setApprovingSheet(true);
    setError('');
    const currentSheet = sheets.find((s) => s.sheet_name === selectedSheet);
    const stmtType = currentSheet?.sheet_type ?? 'ESTADO_RESULTADOS';
    const yearNum = Number.parseInt(periodInput.trim(), 10) || (asOfDate ? Number.parseInt(asOfDate.slice(0, 4), 10) : 2025);

    try {
      const res = await approveImportSheet(importId, selectedSheet, {
        label: periodInput.trim() || String(yearNum),
        year: yearNum,
        statement_type: stmtType,
        as_of_date: asOfDate || undefined,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
        timeframe: timeframe || undefined,
        overwrite,
      });

      if (res.is_duplicate && !overwrite) {
        setDuplicateWarning(res.duplicate_warning ?? 'Ya existen saldos registrados para este período y estado.');
        return;
      }

      setDuplicateWarning(null);
      if (res.success) {
        setSuccessMessage(`✓ Se guardaron ${res.balances_saved} saldos contables de la hoja ${selectedSheet} en la base de datos.`);
        setTimeout(() => {
          setSuccessMessage('');
          onApproved();
        }, 1200);
        await refreshAccountingValidation();
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Error al aprobar la hoja');
    } finally {
      setApprovingSheet(false);
    }
  }

  async function handleApprove() {
    if (!importJob) return;
    setApproving(true);
    setError('');
    try {
      const validation = await refreshAccountingValidation();
      if (!validation.valid) {
        setError('La importación tiene ecuaciones contables pendientes de corregir.');
        return;
      }
      const approved = await approveImport(importId);
      setImportJob(approved);
      onApproved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Error al aprobar la importación');
    } finally {
      setApproving(false);
    }
  }

  const canApprove =
    Boolean(importJob?.period_validated) &&
    !importJob?.period_conflict &&
    (importJob?.review_rows ?? 0) === 0 &&
    importJob?.status !== 'APPROVED';
  const invalidRowIds = collectInvalidRowIds(accountingValidation);

  if (loading) {
    return (
      <div className="workspace-loading-state">
        <p>Cargando espacio de revisión...</p>
      </div>
    );
  }

  return (
    <div className="review-workspace">
      {/* Top bar with back, company/file metadata, period validation */}
      <header className="review-topbar">
        <div className="topbar-left">
          <button type="button" className="secondary-button icon-back" onClick={onBack}>
            ← Volver a selección
          </button>
          <div className="topbar-title-block">
            <span className="eyebrow">{company.name}</span>
            <h1 className="topbar-file-name">{importJob?.file_name ?? 'Archivo Excel'}</h1>
          </div>
        </div>

        <div className="topbar-period-block">
          {sheets.find((s) => s.sheet_name === selectedSheet)?.sheet_type === 'ESTADO_SITUACION_FINANCIERA' ? (
            <label className="period-label">
              Al (Corte):
              <input
                type="date"
                className="date-picker-input"
                value={asOfDate}
                onChange={(e) => {
                  setAsOfDate(e.target.value);
                  if (e.target.value) setPeriodInput(e.target.value.slice(0, 4));
                }}
              />
            </label>
          ) : (
            <>
              <label className="period-label">
                Desde:
                <input
                  type="date"
                  className="date-picker-input"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                />
              </label>
              <label className="period-label">
                Hasta:
                <input
                  type="date"
                  className="date-picker-input"
                  value={periodEnd}
                  onChange={(e) => {
                    setPeriodEnd(e.target.value);
                    if (e.target.value) setPeriodInput(e.target.value.slice(0, 4));
                  }}
                />
              </label>
            </>
          )}
          <label className="period-label">
            Año:
            <input
              className="period-input"
              value={periodInput}
              placeholder="Ej. 2025"
              onChange={(e) => setPeriodInput(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="secondary-button"
            disabled={validatingPeriod || (!periodInput.trim() && !asOfDate && !periodEnd)}
            onClick={() => void handleValidatePeriod()}
          >
            {validatingPeriod ? 'Validando…' : importJob?.period_validated ? '✓ Fechas validadas' : 'Validar fechas'}
          </button>
          {timeframe && (
            <span className="timeframe-pill" title="Clasificación temporal">
              {timeframe}
            </span>
          )}
          {importJob?.period_conflict && (
            <span className="conflict-badge" title="Conflicto entre hojas: elige el año correspondiente">
              ⚠️ Conflicto detectado
            </span>
          )}
        </div>

        <div className="topbar-right">
          <button
            type="button"
            className="primary-button"
            disabled={!canApprove || approving}
            onClick={() => void handleApprove()}
          >
            {approving
              ? 'Aprobando…'
              : importJob?.status === 'APPROVED'
              ? '✓ Importación aprobada'
              : 'Validar y aprobar'}
          </button>
        </div>
      </header>

      {/* Metric counters banner */}
      <section className="review-metrics-banner">
        <div className="metric-pill">
          <span className="metric-count">{importJob?.total_rows ?? 0}</span>
          <span className="metric-label">Filas extraídas</span>
        </div>
        <div className="metric-pill pill-success">
          <span className="metric-count">{importJob?.recognized_rows ?? 0}</span>
          <span className="metric-label">Reconocidas</span>
        </div>
        <div className="metric-pill pill-unknown">
          <span className="metric-count">{importJob?.unknown_rows ?? 0}</span>
          <span className="metric-label">Desconocidas (UNKNOWN)</span>
        </div>
        <div className="metric-pill pill-warning">
          <span className="metric-count">{importJob?.review_rows ?? 0}</span>
          <span className="metric-label">Requieren revisión</span>
        </div>
        <div className="metric-pill pill-danger">
          <span className="metric-count">{importJob?.error_rows ?? 0}</span>
          <span className="metric-label">Errores</span>
        </div>
      </section>

      {error && <div className="workspace-alert alert-error" role="alert">{error}</div>}
      {successMessage && <div className="workspace-alert alert-success">{successMessage}</div>}
      {importJob?.period_conflict && (
        <div className="workspace-alert alert-warning">
          <strong>Atención:</strong> Las hojas del libro contienen distintos años (ej. 2024 y 2025). Valida arriba el período correspondiente a esta importación para poder aprobar.
        </div>
      )}

      <AccountingValidationPanel validation={accountingValidation} />

      {/* Main workspace focused on a single sheet */}
      <main className="review-main-columns">
        <section className="preview-center-area">
          <div className="preview-area-header">
            <div className="preview-title-wrap">
              <h3>Vista del libro: {selectedSheet}</h3>
              {preview && (
                <span className="sheet-row-counter">
                  {preview.rows.length} de {preview.total_rows} filas {preview.truncated ? '(truncado)' : ''}
                </span>
              )}
            </div>
            <div className="preview-header-actions">
              {(() => {
                const pendingCount =
                  preview?.row_details.filter(isPendingPreviewRow).length ?? 0;
                const hasBlocking =
                  accountingValidation?.rules.some(
                    (rule) => rule.status === 'MISMATCH' || rule.status === 'DUPLICATE_CONFLICT',
                  ) ?? false;
                return (
                  <button
                    type="button"
                    className="primary-button small"
                    disabled={approvingSheet || pendingCount > 0 || hasBlocking}
                    onClick={() => void handleApproveSheet(false)}
                  >
                    {approvingSheet
                      ? 'Guardando saldos…'
                      : pendingCount > 0
                      ? `Resolver ${pendingCount} fila(s) para aprobar`
                      : hasBlocking
                      ? 'Corrige la validación contable'
                      : 'Aprobar esta hoja y guardar saldos'}
                  </button>
                );
              })()}
            </div>
          </div>

          <PreviewTable
            columns={preview?.columns ?? []}
            rows={preview?.rows ?? []}
            rowDetails={preview?.row_details ?? []}
            selectedRowId={selectedRow?.import_row_id}
            invalidRowIds={invalidRowIds}
            onSelectRow={(rowDetail) => setSelectedRow(rowDetail)}
          />
        </section>

        <RowReviewPanel
          companyId={importJob?.company_id ?? (Number(company.id) || 1)}
          sheetType={sheets.find((s) => s.sheet_name === selectedSheet)?.sheet_type}
          selectedRow={selectedRow}
          onMatch={handleMatch}
          onIgnore={handleIgnore}
          onClassify={handleClassify}
          onUpdateFinancialLine={handleUpdateFinancialLine}
          onClose={() => setSelectedRow(null)}
        />
      </main>

      {/* Duplicate warning modal */}
      {duplicateWarning && (
        <div className="duplicate-dialog-backdrop" role="presentation">
          <div className="duplicate-dialog" role="dialog" aria-modal="true">
            <div className="duplicate-dialog-icon">⚠️</div>
            <h4>Alerta de duplicado contable</h4>
            <p className="duplicate-warning-text">{duplicateWarning}</p>
            <p className="duplicate-explanation">
              Se encontraron saldos registrados previamente para esta empresa y fecha/período.
              ¿Deseas sobrescribir los saldos con los datos de esta hoja?
            </p>
            <div className="duplicate-dialog-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setDuplicateWarning(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={() => void handleApproveSheet(true)}
              >
                Sobrescribir y guardar saldos
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
