import type { Company } from '../app-state';

export function FilesPage({ company, onImport }: { company: Company; onImport: () => void }) {
  return <section className="page-stack"><div className="section-heading"><div><p className="eyebrow">FUENTES DE DATOS</p><h2>Archivos</h2><p>Historial de archivos importados para {company.name}.</p></div><button className="primary-button" type="button" onClick={onImport}>+ Importar datos</button></div><section className="content-card files-empty"><span className="upload-icon">□</span><h2>Aún no hay archivos importados</h2><p>Los libros Excel de esta empresa aparecerán aquí con su estado y período.</p><button className="secondary-button" type="button" onClick={onImport}>Seleccionar archivo</button></section></section>;
}
