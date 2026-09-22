import { useEffect, useState } from 'react';
import { ensureCompany, listCompanyImports, type ImportResult } from '../api';
import type { Company } from '../app-state';

type FilesPageProps = {
  company: Company;
  onImport: () => void;
  onOpenReview?: (importId: number) => void;
};

const STATUS_CONFIG: Record<string, { label: string; badgeClass: string }> = {
  APPROVED: { label: 'Aprobada', badgeClass: 'pill-matched' },
  READY_FOR_REVIEW: { label: 'Requiere revisión', badgeClass: 'pill-unknown' },
  ANALYZING: { label: 'Analizando…', badgeClass: 'pill-needs_review' },
  UPLOADED: { label: 'Subido', badgeClass: 'pill-ignored' },
  FAILED: { label: 'Error', badgeClass: 'badge-error' },
};

export function FilesPage({ company, onImport, onOpenReview }: FilesPageProps) {
  const [imports, setImports] = useState<ImportResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const backendCompany = await ensureCompany(company);
        const data = await listCompanyImports(backendCompany.id);
        setImports(data);
      } catch {
        setImports([]);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [company.id]);

  return (
    <section className="page-stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">FUENTES DE DATOS</p>
          <h2>Archivos</h2>
          <p>Historial de archivos contables importados para {company.name}.</p>
        </div>
        <button className="primary-button" type="button" onClick={onImport}>
          + Importar datos
        </button>
      </div>

      {loading && (
        <section className="content-card files-empty">
          <p>Cargando archivos contables...</p>
        </section>
      )}

      {!loading && imports.length === 0 && (
        <section className="content-card files-empty">
          <span className="upload-icon">□</span>
          <h2>Aún no hay archivos importados</h2>
          <p>Los libros Excel de esta empresa aparecerán aquí con su estado, período y detalle de filas.</p>
          <button className="secondary-button" type="button" onClick={onImport}>
            Seleccionar archivo
          </button>
        </section>
      )}

      {!loading && imports.length > 0 && (
        <div className="content-card files-history-card">
          <table className="files-history-table">
            <thead>
              <tr>
                <th>Archivo</th>
                <th>Período</th>
                <th>Estado</th>
                <th>Filas</th>
                <th>Reconocidas</th>
                <th>Desconocidas</th>
                <th>Pendientes</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((item) => {
                const statusInfo = STATUS_CONFIG[item.status] ?? {
                  label: item.status,
                  badgeClass: 'pill-ignored',
                };
                return (
                  <tr key={item.id} className="history-row">
                    <td className="history-file-name">
                      <strong>{item.file_name}</strong>
                    </td>
                    <td>
                      <span className="history-period-pill">
                        {item.detected_period_label || '— Sin validar —'}
                      </span>
                    </td>
                    <td>
                      <span className={`status-pill ${statusInfo.badgeClass}`}>
                        {statusInfo.label}
                      </span>
                    </td>
                    <td>{item.total_rows}</td>
                    <td className="cell-success">{item.recognized_rows}</td>
                    <td className="cell-unknown">{item.unknown_rows}</td>
                    <td className="cell-warning">{item.review_rows}</td>
                    <td>
                      {onOpenReview && (
                        <button
                          type="button"
                          className={
                            item.status === 'APPROVED' ? 'secondary-button small' : 'primary-button small'
                          }
                          onClick={() => onOpenReview(item.id)}
                        >
                          {item.status === 'APPROVED' ? 'Ver libro' : 'Revisar libro'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
