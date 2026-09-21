import { useState, type FormEvent } from 'react';
import type { Company } from '../app-state';

type CompaniesPageProps = {
  companies: Company[];
  onSelect: (companyId: string) => void;
  onCreate: (company: Company) => void;
};

export function CompaniesPage({ companies, onSelect, onCreate }: CompaniesPageProps) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [country, setCountry] = useState('El Salvador');

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanName = name.trim();
    if (!cleanName) return;
    onCreate({
      id: `company-${Date.now()}`,
      name: cleanName,
      currency,
      country,
      fiscalCloseMonth: '',
      lastData: 'Sin datos importados',
      periods: [],
    });
    setName(''); setShowForm(false);
  }

  return (
    <main className="companies-page">
      <div className="page-heading">
        <div><p className="eyebrow">CELESTE ANILISYS</p><h1>Empresas</h1><p>Selecciona una empresa para entrar a su espacio financiero.</p></div>
        <button className="primary-button" type="button" onClick={() => setShowForm(true)}>+ Nueva empresa</button>
      </div>
      {showForm && <form className="content-card company-form" onSubmit={submit}>
        <div className="form-heading"><div><span className="welcome-kicker">NUEVO ESPACIO</span><h2>Crear empresa</h2></div><button className="icon-button" type="button" onClick={() => setShowForm(false)} aria-label="Cerrar">×</button></div>
        <div className="form-grid">
          <label>Nombre de la empresa<input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej. Comercial XYZ" /></label>
          <label>Moneda<select value={currency} onChange={(e) => setCurrency(e.target.value)}><option>USD</option><option>EUR</option><option>MXN</option></select></label>
          <label>País<input value={country} onChange={(e) => setCountry(e.target.value)} /></label>
        </div>
        <div className="form-actions"><button className="secondary-button" type="button" onClick={() => setShowForm(false)}>Cancelar</button><button className="primary-button" type="submit">Crear empresa</button></div>
      </form>}
      <section className="company-grid" aria-label="Empresas disponibles">
        {companies.map((company) => <button className="company-card" type="button" key={company.id} onClick={() => onSelect(company.id)}>
          <span className="company-avatar">{company.name.slice(0, 2).toUpperCase()}</span><span className="company-card-copy"><strong>{company.name}</strong><small>{company.industry ?? 'Empresa'} · {company.currency}</small><small>{company.periods.length ? `Datos hasta ${company.lastData}` : 'Sin datos importados'}</small></span><span className="card-arrow">→</span>
        </button>)}
        <button className="company-card add-company-card" type="button" onClick={() => setShowForm(true)}><span className="add-icon">+</span><span><strong>Agregar empresa</strong><small>Crea un nuevo espacio aislado</small></span></button>
      </section>
    </main>
  );
}
