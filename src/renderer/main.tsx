import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { demoCompanies, type Company } from './app-state';
import { ContextHeader } from './components/ContextHeader';
import { ImportWizard } from './components/imports/ImportWizard';
import { Sidebar } from './components/Sidebar';
import { CompaniesPage } from './pages/CompaniesPage';
import { ComparisonPage } from './pages/ComparisonPage';
import { DashboardPage } from './pages/DashboardPage';
import { FilesPage } from './pages/FilesPage';
import { ImportReviewPage } from './pages/ImportReviewPage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { SheetSelectionPage } from './pages/SheetSelectionPage';
import {
  initialPath,
  isReviewPath,
  isSelectSheetPath,
  parseImportIdFromPath,
  parseSheetNameFromReviewPath,
  reviewSheetPath,
  selectSheetPath,
  showsGlobalContextControls,
} from './navigation';
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

  if (isSelectSheetPath(activePath)) {
    const selectImportId = parseImportIdFromPath(activePath);
    if (selectImportId !== null) {
      return (
        <div className="app-shell review-mode">
          <SheetSelectionPage
            importId={selectImportId}
            company={company}
            onBack={() => setActivePath('/files')}
            onSelectSheet={(name) => setActivePath(reviewSheetPath(selectImportId, name))}
          />
        </div>
      );
    }
  }

  if (isReviewPath(activePath)) {
    const reviewImportId = parseImportIdFromPath(activePath);
    const reviewSheetName = parseSheetNameFromReviewPath(activePath);
    if (reviewImportId !== null && reviewSheetName !== null) {
      return (
        <div className="app-shell review-mode">
          <ImportReviewPage
            importId={reviewImportId}
            company={company}
            sheetName={reviewSheetName}
            onBack={() => setActivePath(selectSheetPath(reviewImportId))}
            onApproved={() => setActivePath(selectSheetPath(reviewImportId))}
          />
        </div>
      );
    }
  }

  function renderPage() {
    if (activePath === '/dashboard') return <DashboardPage company={company} onImport={() => setShowImport(true)} onFiles={() => setActivePath('/files')} />;
    if (activePath === '/files') return <FilesPage company={company} onImport={() => setShowImport(true)} onOpenReview={(id) => setActivePath(selectSheetPath(id))} />;
    if (activePath === '/statements') return <PlaceholderPage title="Estados financieros" description="Aquí veremos balance general, estado de resultados y flujo de efectivo por período." />;
    if (activePath === '/analysis') return <PlaceholderPage title="Análisis" description="Aquí estarán los indicadores, ratios y análisis financiero de la empresa." />;
    if (activePath === '/comparisons') return <ComparisonPage company={company} onFiles={() => setActivePath('/files')} />;
    return <PlaceholderPage title="Configuración" description="Administra las preferencias y datos generales de esta empresa." />;
  }

  return <div className="app-shell">
    <Sidebar company={company} companies={companies} activePath={activePath} onNavigate={setActivePath} onCompanyChange={enterCompany} onNewCompany={leaveCompany} onAllCompanies={leaveCompany} />
    <main className="main-content">
      <ContextHeader
        company={company}
        period={period}
        view={view}
        showControls={showsGlobalContextControls(activePath)}
        onPeriodChange={setPeriod}
        onViewChange={setView}
      />
      {renderPage()}
    </main>
    {showImport && (
      <ImportWizard
        company={company}
        onClose={() => setShowImport(false)}
        onOpenReview={(importId) => {
          setShowImport(false);
          setActivePath(selectSheetPath(importId));
        }}
      />
    )}
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
