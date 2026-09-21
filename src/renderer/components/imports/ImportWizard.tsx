import { useRef, useState, type ChangeEvent } from 'react';
import { fileNameFromPath, isSupportedFile } from '../../file-selection';
import { analyzeImport, ensureCompany, ensurePeriod, fileFromBase64, getImportIssues, getImportSheets, uploadImport, type ImportIssue, type ImportResult, type ImportSheet } from '../../api';
import type { Company } from '../../app-state';

type ImportWizardProps = { company: Company; onClose: () => void };

export function ImportWizard({ company, onClose }: ImportWizardProps) {
  const [period, setPeriod] = useState(company.periods.at(-1) ?? String(new Date().getFullYear()));
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [browserFiles, setBrowserFiles] = useState<File[]>([]);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [sheets, setSheets] = useState<ImportSheet[]>([]);
  const [issues, setIssues] = useState<ImportIssue[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function chooseFiles() {
    if (window.electronAPI) {
      const files = await window.electronAPI.selectFiles();
      setSelectedFiles(files.filter(isSupportedFile)); setBrowserFiles([]); setResult(null); setError('');
      return;
    }
    inputRef.current?.click();
  }

  function handleBrowserSelection(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []).filter((file) => isSupportedFile(file.name));
    setBrowserFiles(files); setSelectedFiles(files.map((file) => file.name)); setResult(null); setError('');
  }

  async function analyze() {
    setLoading(true); setError('');
    try {
      const backendCompany = await ensureCompany(company);
      const backendPeriod = await ensurePeriod(backendCompany.id, period);
      const files = window.electronAPI
        ? await Promise.all(selectedFiles.map(async (path) => { const file = await window.electronAPI!.readFile(path); return fileFromBase64(file.name, file.data); }))
        : browserFiles;
      if (!files.length) throw new Error('Selecciona al menos un archivo Excel válido');
      const uploaded = await uploadImport(backendCompany.id, backendPeriod.id, files[0]);
      const analyzed = await analyzeImport(uploaded.id);
      const [sheetResponse, issueResponse] = await Promise.all([getImportSheets(uploaded.id), getImportIssues(uploaded.id)]);
      setResult(analyzed); setSheets(sheetResponse.sheets); setIssues(issueResponse.rows);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo conectar con el backend');
    } finally { setLoading(false); }
  }

  return <div className="modal-backdrop" role="presentation"><section className="import-modal" role="dialog" aria-modal="true" aria-labelledby="import-title">
    <div className="modal-heading"><div><span className="eyebrow">{company.name}</span><h2 id="import-title">Importar datos</h2></div><button className="icon-button" type="button" onClick={onClose} aria-label="Cerrar">×</button></div>
    <div className="wizard-steps"><span className={!result ? 'current' : ''}>1 Seleccionar Excel</span><span className={result ? 'current' : ''}>2 Detectar información</span><span>3 Revisar</span><span>4 Confirmar</span></div>
    <label className="field-label">Período de trabajo<select value={period} onChange={(event) => setPeriod(event.target.value)}>{company.periods.length ? company.periods.map((availablePeriod) => <option key={availablePeriod}>{availablePeriod}</option>) : <option>{period}</option>}</select></label>
    <button className="dropzone" type="button" onClick={chooseFiles}><span className="upload-icon small">↑</span><strong>Arrastra aquí tu archivo Excel</strong><span>o haz clic para seleccionar · .xlsx, .xlsm</span></button>
    <input ref={inputRef} className="visually-hidden" type="file" accept=".xlsx,.xlsm" multiple onChange={handleBrowserSelection} />
    {selectedFiles.length > 0 && <div className="selected-files">{selectedFiles.map((file) => <span key={file}>✓ {fileNameFromPath(file)}</span>)}</div>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {result && <div className="import-review"><div className="import-result"><strong>Archivo analizado correctamente</strong><span>{result.total_rows} filas detectadas · {result.recognized_rows} reconocidas · {result.review_rows} requieren revisión</span></div><strong className="review-title">Hojas detectadas</strong><div className="sheet-list">{sheets.map((sheet) => <span key={sheet.sheet_name}>✓ {sheet.sheet_name} <small>{sheet.sheet_type}</small></span>)}</div>{issues.length > 0 && <><strong className="review-title warning">Filas para revisión</strong><div className="issue-list">{issues.slice(0, 5).map((issue) => <span key={`${issue.source_sheet}-${issue.source_row}`}>{issue.source_sheet} · fila {issue.source_row} · {issue.original_name ?? 'Sin nombre'} <small>{issue.status}</small></span>)}</div></>}</div>}
    <div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose}>Cerrar</button><button className="primary-button" type="button" disabled={!selectedFiles.length || loading || Boolean(result)} onClick={() => void analyze()}>{loading ? 'Analizando…' : result ? 'Analizado' : 'Analizar archivo'}</button></div>
  </section></div>;
}
