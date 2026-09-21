import { StrictMode, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { fileNameFromPath, isSupportedFile } from './file-selection';
import { menuItems } from './navigation';
import './styles.css';

function App() {
  const [activePath, setActivePath] = useState('/');
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  async function chooseFiles() {
    if (window.electronAPI) {
      setSelectedFiles(await window.electronAPI.selectFiles());
      return;
    }
    inputRef.current?.click();
  }

  function handleBrowserSelection(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
      .filter((file) => isSupportedFile(file.name))
      .map((file) => file.name);
    setSelectedFiles(files);
  }

  const isUpload = activePath === '/subida';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">CA</div>
          <div>
            <strong>Celeste</strong>
            <span>Anilisys</span>
          </div>
        </div>

        <nav className="menu" aria-label="Menú principal">
          <span className="menu-title">MENÚ PRINCIPAL</span>
          {menuItems.map((item) => (
            <button
              className={`menu-item ${activePath === item.path ? 'active' : ''}`}
              key={item.id}
              onClick={() => setActivePath(item.path)}
              type="button"
            >
              <span className="menu-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">Análisis financiero</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">CELeste ANILISYS</p>
            <h1>{isUpload ? 'SUBIDA' : 'Resumen'}</h1>
          </div>
          <div className="status-dot" title="Aplicación local" />
        </header>

        {isUpload ? (
          <section className="content-card upload-card">
            <div className="upload-icon" aria-hidden="true">↑</div>
            <h2>Subir archivos financieros</h2>
            <p>Selecciona archivos XLS, XLSX o CSV para comenzar.</p>
            <input
              accept=".xls,.xlsx,.csv"
              className="visually-hidden"
              multiple
              onChange={handleBrowserSelection}
              ref={inputRef}
              type="file"
            />
            <button className="primary-button" onClick={chooseFiles} type="button">
              Subir archivos
            </button>
            {selectedFiles.length > 0 && (
              <div className="selected-files" aria-live="polite">
                <strong>Archivos seleccionados</strong>
                {selectedFiles.map((file) => (
                  <span key={file}>✓ {fileNameFromPath(file)}</span>
                ))}
              </div>
            )}
          </section>
        ) : (
          <section className="content-card empty-card">
            <span className="welcome-kicker">PRÓXIMAMENTE</span>
            <h2>Tu resumen financiero</h2>
            <p>Selecciona SUBIDA en el menú lateral para cargar tus primeros archivos.</p>
          </section>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
