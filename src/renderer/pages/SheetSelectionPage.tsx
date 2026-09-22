import { useEffect, useState } from 'react';
import { getImport, getImportSheets, type ImportResult, type ImportSheet } from '../api';
import type { Company } from '../app-state';

type SheetSelectionPageProps = {
  importId: number;
  company: Company;
  onBack: () => void;
  onSelectSheet: (sheetName: string) => void;
};

const SHEET_TYPE_LABELS: Record<string, string> = {
  BALANCE_COMPROBACION: 'Balance de Comprobación',
  ESTADO_SITUACION_FINANCIERA: 'Balance General',
  ESTADO_RESULTADOS: 'Estado de Resultados',
  FLUJO_EFECTIVO: 'Flujo de Efectivo',
  DESCONOCIDO: 'Hoja auxiliar',
};

export function SheetSelectionPage({
  importId,
  company,
  onBack,
  onSelectSheet,
}: SheetSelectionPageProps) {
  const [importJob, setImportJob] = useState<ImportResult | null>(null);
  const [sheets, setSheets] = useState<ImportSheet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError('');
      try {
        const [job, sheetsData] = await Promise.all([getImport(importId), getImportSheets(importId)]);
        setImportJob(job);
        setSheets(sheetsData.sheets);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Error al cargar las hojas');
      } finally {
        setLoading(false);
      }
    }
    void init();
  }, [importId]);

  const validSheets = sheets.filter((s) => s.status !== 'DISCARDED');
  const discardedSheets = sheets.filter((s) => s.status === 'DISCARDED');

  if (loading) {
    return (
      <div className="workspace-loading-state">
        <p>Analizando hojas del archivo...</p>
      </div>
    );
  }

  return (
    <div className="review-workspace">
      <header className="review-topbar">
        <div className="topbar-left">
          <button type="button" className="secondary-button icon-back" onClick={onBack}>
            ← Volver a Archivos
          </button>
          <div className="topbar-title-block">
            <span className="eyebrow">{company.name}</span>
            <h1 className="topbar-file-name">{importJob?.file_name ?? 'Archivo Excel'}</h1>
          </div>
        </div>
        <div className="topbar-right">
          <span className="detection-summary-pill">
            {validSheets.length} estado(s) detectado(s) · {discardedSheets.length} hoja(s) no analizable(s)
          </span>
        </div>
      </header>

      <main className="sheet-selection-main">
        <div className="selection-heading">
          <h2>Selecciona un estado financiero para revisar</h2>
          <p>
            Este archivo contiene varias hojas. Cada una es un estado financiero independiente con su
            propio período. Revisa y aprueba uno a la vez; luego podrás volver aquí para cargar otro.
          </p>
        </div>

        {error && <div className="workspace-alert alert-error" role="alert">{error}</div>}

        {validSheets.length === 0 && (
          <div className="selection-empty-state">
            <span className="upload-icon">□</span>
            <h3>No se detectaron estados financieros</h3>
            <p>Ninguna hoja de este archivo pudo reconocerse como un estado financiero.</p>
          </div>
        )}

        <div className="sheet-card-grid">
          {validSheets.map((sheet) => {
            const displayType = SHEET_TYPE_LABELS[sheet.sheet_type] ?? sheet.sheet_type;
            const isApproved = sheet.status === 'APPROVED';
            return (
              <button
                key={sheet.sheet_name}
                type="button"
                className={`sheet-select-card ${isApproved ? 'card-approved' : ''}`}
                onClick={() => onSelectSheet(sheet.sheet_name)}
              >
                <div className="sheet-select-card-head">
                  <span className="sheet-card-bullet">{isApproved ? '✓' : '●'}</span>
                  <strong>{sheet.sheet_name}</strong>
                  {isApproved && <span className="sheet-approved-tag">Aprobada</span>}
                </div>
                <span className="sheet-select-card-type">{displayType}</span>
                <span className="sheet-select-card-date">
                  {sheet.date_label || 'Período no detectado'}
                </span>
                <div className="sheet-select-card-stats">
                  <span>{sheet.total_rows} filas</span>
                  <span className={sheet.review_rows > 0 ? 'stat-warning' : 'stat-ok'}>
                    {sheet.review_rows > 0 ? `${sheet.review_rows} por revisar` : 'Lista para revisar'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {discardedSheets.length > 0 && (
          <section className="discarded-sheets-section">
            <h3 className="discarded-title">Hojas no analizables</h3>
            <p className="discarded-hint">
              Estas hojas no se reconocieron como un estado financiero y no se podrán cargar.
            </p>
            <ul className="discarded-list">
              {discardedSheets.map((sheet) => (
                <li key={sheet.sheet_name}>
                  <span className="discarded-sheet-name">{sheet.sheet_name}</span>
                  <span className="discarded-sheet-reason">
                    {sheet.discard_reason || 'No reconocida como estado financiero'}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
