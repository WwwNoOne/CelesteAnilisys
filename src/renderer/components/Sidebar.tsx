import type { Company } from '../app-state';
import { menuItems } from '../navigation';

type SidebarProps = {
  company: Company;
  companies: Company[];
  activePath: string;
  onNavigate: (path: string) => void;
  onCompanyChange: (companyId: string) => void;
  onNewCompany: () => void;
  onAllCompanies: () => void;
};

export function Sidebar({
  company,
  companies,
  activePath,
  onNavigate,
  onCompanyChange,
  onNewCompany,
  onAllCompanies,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">CA</div>
        <div><strong>Celeste</strong><span>Anilisys</span></div>
      </div>

      <div className="company-switcher">
        <span className="menu-title">EMPRESA ACTIVA</span>
        <select
          aria-label="Empresa activa"
          value={company.id}
          onChange={(event) => onCompanyChange(event.target.value)}
        >
          {companies.map((availableCompany) => (
            <option key={availableCompany.id} value={availableCompany.id}>{availableCompany.name}</option>
          ))}
        </select>
        <button type="button" onClick={onNewCompany}>+ Nueva empresa</button>
        <button type="button" onClick={onAllCompanies}>Ver todas las empresas</button>
      </div>

      <nav className="menu" aria-label="Menú de empresa">
        <span className="menu-title">ESPACIO DE TRABAJO</span>
        {menuItems.map((item) => (
          <button
            className={`menu-item ${activePath === item.path ? 'active' : ''}`}
            key={item.id}
            onClick={() => onNavigate(item.path)}
            type="button"
          >
            <span className="menu-icon" aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">Análisis financiero</div>
    </aside>
  );
}
