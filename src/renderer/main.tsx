import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { demoCompanies, type Company } from './app-state';
import { ContextHeader } from './components/ContextHeader';
import { ImportWizard } from './components/imports/ImportWizard';
import { Sidebar } from './components/Sidebar';
import { CompaniesPage } from './pages/CompaniesPage';
import { DashboardPage } from './pages/DashboardPage';
import { FilesPage } from './pages/FilesPage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { initialPath } from './navigation';
import './styles.css';

function App() {
  const [companies, setCompanies] = useState<Company[]>(demoCompanies);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [activePath, setActivePath] = useState(initialPath);
  const [period, setPeriod] = useState('');
  const [view, setView] = useState('Mensual');
  const [showImport, setShowImport] = useState(false);
  const company = companies.find((item) => item.id === activeCompanyId);

  function enterCompany(companyId: string) {
    const nextCompany = companies.find((item) => item.id === companyId);
    setActiveCompanyId(companyId);
    setPeriod(nextCompany?.periods.at(-1) ?? '');
    setActivePath('/dashboard');
  }

  function leaveCompany() {
    setActiveCompanyId(null);
    setActivePath(initialPath);
  }

  function addCompany(nextCompany: Company) {
    setCompanies((current) => [...current, nextCompany]);
    enterCompany(nextCompany.id);
  }

  if (!company) return <CompaniesPage companies={companies} onSelect={enterCompany} onCreate={addCompany} />;

  function renderPage() {
    if (activePath === '/dashboard') return <DashboardPage company={company} onImport={() => setShowImport(true)} onFiles={() => setActivePath('/files')} />;
    if (activePath === '/files') return <FilesPage company={company} onImport={() => setShowImport(true)} />;
    if (activePath === '/statements') return <PlaceholderPage title="Estados financieros" description="Aquí veremos balance general, estado de resultados y flujo de efectivo por período." />;
    if (activePath === '/analysis') return <PlaceholderPage title="Análisis" description="Aquí estarán los indicadores, ratios y análisis financiero de la empresa." />;
    if (activePath === '/comparisons') return <PlaceholderPage title="Comparaciones" description="Compara años, meses y períodos cuando los datos estén disponibles." />;
    return <PlaceholderPage title="Configuración" description="Administra las preferencias y datos generales de esta empresa." />;
  }

  return <div className="app-shell">
    <Sidebar company={company} companies={companies} activePath={activePath} onNavigate={setActivePath} onCompanyChange={enterCompany} onNewCompany={leaveCompany} onAllCompanies={leaveCompany} />
    <main className="main-content">
      <ContextHeader company={company} period={period} view={view} onPeriodChange={setPeriod} onViewChange={setView} />
      {renderPage()}
    </main>
    {showImport && <ImportWizard company={company} onClose={() => setShowImport(false)} />}
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
