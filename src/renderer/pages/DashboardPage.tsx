import type { Company } from '../app-state';

type DashboardPageProps = { company: Company; onImport: () => void; onFiles: () => void };

export function DashboardPage({ company, onImport, onFiles }: DashboardPageProps) {
  const hasData = company.periods.length > 0;
  return <section className="page-stack">
    <div className="metric-grid"><article className="metric-card blue"><span>ACTIVOS TOTALES</span><strong>{hasData ? '$0.00' : '—'}</strong><small>Próximamente</small></article><article className="metric-card cyan"><span>INGRESOS</span><strong>{hasData ? '$0.00' : '—'}</strong><small>Selecciona un período</small></article><article className="metric-card light"><span>ÚLTIMA ACTUALIZACIÓN</span><strong>{hasData ? company.lastData : 'Sin datos'}</strong><small>{company.currency}</small></article></div>
    <section className="content-card dashboard-empty"><span className="upload-icon">↑</span><span className="welcome-kicker">CENTRO DE CONTROL</span><h2>{hasData ? 'Resumen financiero listo para crecer' : 'Comienza importando tus datos'}</h2><p>Los indicadores y gráficos de {company.name} aparecerán aquí cuando conectemos el análisis financiero.</p><div className="quick-actions"><button className="primary-button" type="button" onClick={onImport}>+ Importar datos</button><button className="secondary-button" type="button" onClick={onFiles}>Ver archivos</button></div></section>
  </section>;
}
